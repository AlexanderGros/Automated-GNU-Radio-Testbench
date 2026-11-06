#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MASTER_CAMPAIGN_V5.py — à lancer sur PC2 (RX)

Script maître de campagne automatique multi-modulation V5.
Utilise les récepteurs V5 avec boucles de synchronisation adaptatives.
"""

import zmq
import subprocess
import sys
import os
import time
import numpy as np
import openpyxl
from itertools import product
from datetime import datetime

TX_PC_IP = "10.0.0.120"
TX_ZMQ_PORT = 6000

TUN_FREQ    = 2.4e9
TX_GAIN     = 65

IQ_BASE_DIR = r"C:\Users\Admin\Desktop\tests/IQ_V5"
EXCEL_PATH  = r"C:\Users\Admin\Desktop\tests\resultats_V5.xlsx"

NB_SYMBOLES_CIBLE = 100000
USRP_RELEASE_S  = 4.0

_THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
_RX_V5_DIR = _THIS_DIR

warmup_para = 2.0

CAMPAIGN_CONFIG = {
    "BPSK": {
        "rx_script":        os.path.join(_RX_V5_DIR, "RX_BPSK_UHD_auto_V5.py"),
        "samp_rate":        500000,
        "alphas":           np.array([0.4]),
        "sps_list":         [2, 4, 6, 8],
        "warmup_s":         warmup_para,
        "tx_settle_s":      4.0,
        "rx_gain":          55,
        "bits_par_symbole": 1,
        "timeout_s":        90,
        "osps_corrected":   2,
    },
    "QPSK": {
        "rx_script":        os.path.join(_RX_V5_DIR, "RX_QPSK_UHD_auto_V5.py"),
        "samp_rate":        500000,
        "alphas":           np.array([0.4]),
        "sps_list":         [2, 4, 6, 8],
        "warmup_s":         warmup_para,
        "tx_settle_s":      4.0,
        "rx_gain":          55,
        "bits_par_symbole": 2,
        "timeout_s":        200,
        "osps_corrected":   2,
    },
    "8PSK": {
        "rx_script":        os.path.join(_RX_V5_DIR, "RX_8PSK_UHD_auto_V5.py"),
        "samp_rate":        500000,
        "alphas":           np.array([0.4]),
        "sps_list":         [2, 4, 6, 8],
        "warmup_s":         warmup_para,
        "tx_settle_s":      5.0,
        "rx_gain":          55,
        "bits_par_symbole": 3,
        "timeout_s":        200,
        "osps_corrected":   2,
    },
    "QAM16": {
        "rx_script":        os.path.join(_RX_V5_DIR, "RX_QAM16_UHD_auto_V5.py"),
        "samp_rate":        1000000,
        "alphas":           np.array([0.4]),
        "sps_list":         [6, 8, 10, 12],
        "warmup_s":         warmup_para,
        "tx_settle_s":      5.0,
        "rx_gain":          55,
        "bits_par_symbole": 4,
        "timeout_s":        200,
        "osps_corrected":   2,
    },
}

MODULATION_ORDER = ["8PSK", "QPSK", "QAM16", "BPSK"]

def estimate_duration():
    total_s = 0
    print("┌───────────────────────────────────────────────────────────────────┐")
    print("│            MASTER CAMPAIGN V5 — Estimation durée totale           │")
    print("├───────────┬────────┬──────────────┬───────────────────────────────┤")
    print("│ Modulation│ combos │ ~s / combo   │ Durée estimée                 │")
    print("├───────────┼────────┼──────────────┼───────────────────────────────┤")
    for mod in MODULATION_ORDER:
        cfg      = CAMPAIGN_CONFIG[mod]
        n_combos = len(cfg["alphas"]) * len(cfg["sps_list"])
        mod_s = 0
        for sps in cfg["sps_list"]:
            capture_raw_s  = NB_SYMBOLES_CIBLE * sps / cfg["samp_rate"]
            capture_corr_s = NB_SYMBOLES_CIBLE * cfg["osps_corrected"] / cfg["samp_rate"]
            s_combo = (cfg["tx_settle_s"]
                       + 2 * cfg["warmup_s"]
                       + capture_raw_s + capture_corr_s
                       + 3 * USRP_RELEASE_S + 20)
            mod_s += len(cfg["alphas"]) * s_combo
        s_combo = mod_s / n_combos
        total_s += mod_s
        print(f"│ {mod:<10}│ {n_combos:>6} │ {s_combo:>12.0f} │ ~{mod_s/60:>6.1f} min"
              f"{'':>18}│")
    print("├───────────┴────────┴─────────_─────┴──────────────────────────────┤")
    print(f"│  TOTAL                              ~{total_s/60:>7.1f} min  "
          f"(~{total_s/3600:.2f} h)       │")
    print("└───────────────────────────────────────────────────────────────────┘\n")
    return total_s


def send_tx_start(sock, modulation, alpha, sps):
    sock.send_json({
        "cmd":        "start",
        "modulation": modulation,
        "alpha":      float(alpha),
        "sps":        int(sps),
    })
    rep = sock.recv_json()
    return rep.get("status") == "ok"


def launch_rx(rx_script, modulation, samp_rate, alpha, sps, capture, iq_dir, warmup_s,
              rx_gain, tun_freq):
    iq_filename = f"{modulation}_a{alpha:.3f}_sps{sps}_{capture}.bin"
    iq_path     = os.path.join(iq_dir, iq_filename)

    if os.path.exists(iq_path):
        os.remove(iq_path)

    cmd = [
        sys.executable, rx_script,
        "--samp-rate",          str(int(samp_rate)),
        "--roll-off",           str(float(alpha)),
        "--samples-per-symbol", str(int(sps)),
        "--iq-dir",             iq_dir,
        "--capture",            capture,
        "--warmup-s",           str(warmup_s),
        "--rx-gain",            str(int(rx_gain)),
        "--tun-freq",           str(tun_freq),
    ]
    print(f"  [RX] Lancement V5 : alpha={alpha:.3f}  sps={sps}  capture={capture}")
    proc = subprocess.Popen(cmd)
    return proc, iq_path


def wait_stable_samples(iq_path, n_samples, warmup_s, timeout):
    print(f"    → Attente apparition fichier IQ (warmup RX {warmup_s}s en cours)...")
    deadline = time.time() + timeout + warmup_s
    while time.time() < deadline:
        if os.path.exists(iq_path) and os.path.getsize(iq_path) > 0:
            break
        time.sleep(0.5)
    else:
        print("    ✗ Fichier IQ n'est jamais apparu (timeout)")
        return False

    target_bytes = n_samples * 8
    print(f"    → Fichier IQ actif. Capture de {n_samples} samples ({target_bytes} bytes)...")
    deadline2 = time.time() + timeout
    while time.time() < deadline2:
        if os.path.exists(iq_path) and os.path.getsize(iq_path) >= target_bytes:
            return True
        time.sleep(0.2)

    print("    ✗ Timeout : pas assez de samples capturés")
    return False


def stop_proc(proc, timeout=6):
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print("    ⚠ terminate() timeout → kill()")
        proc.kill()
        proc.wait()


def init_excel(path):
    if os.path.exists(path):
        wb = openpyxl.load_workbook(path)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "timestamp", "modulation", "alpha", "sps", "mode",
            "samp_rate", "debit_symboles_baud",
            "tun_freq_Hz", "tx_gain_dB", "rx_gain_dB",
            "warmup_s", "nb_symboles_cible",
            "nb_samples", "nb_symboles", "nb_bits",
            "taille_fichier_octets", "fichier_iq",
            "duree_run_s", "statut",
        ])
        wb.save(path)
    return wb, ws


def run_modulation_campaign(modulation, cfg, sock, wb, ws):
    iq_dir = os.path.join(IQ_BASE_DIR, modulation)
    os.makedirs(iq_dir, exist_ok=True)

    combos  = list(product(cfg["alphas"], cfg["sps_list"]))
    n_total = len(combos)
    ok_count = 0

    osps_corr = cfg["osps_corrected"]

    print(f"\n{'═'*65}")
    print(f"  MODULATION V5 : {modulation}  |  {n_total} combinaisons")
    print(f"  warmup={cfg['warmup_s']}s | cible={NB_SYMBOLES_CIBLE} symboles | "
          f"rx_gain={cfg['rx_gain']}dB | osps_corr={osps_corr} | sps_list={cfg['sps_list']}")
    print(f"{'═'*65}\n")

    for idx, (alpha, sps) in enumerate(combos):
        print(f"\n{'─'*60}")
        print(f"  [{modulation}] [{idx+1}/{n_total}]  alpha={alpha:.3f}   sps={sps}")
        print(f"{'─'*60}")

        NB_SAMPLES_RAW  = NB_SYMBOLES_CIBLE * sps
        NB_SAMPLES_CORR = NB_SYMBOLES_CIBLE * osps_corr

        print(f"  → Commande TX ({modulation}, alpha={alpha:.3f}, sps={sps})...")
        if not send_tx_start(sock, modulation, alpha, sps):
            print("  ✗ TX n'a pas répondu OK — combinaison ignorée")
            continue

        print(f"  → TX démarré. Stabilisation ({cfg['tx_settle_s']}s)...")
        time.sleep(cfg["tx_settle_s"])

        print(f"  → Run 1/2 : capture RAW...")
        rx_proc, iq_path_raw = launch_rx(
            cfg["rx_script"], modulation, cfg["samp_rate"],
            alpha, sps, "raw", iq_dir, cfg["warmup_s"],
            cfg["rx_gain"], TUN_FREQ,
        )
        t0 = time.time()
        ok_raw = wait_stable_samples(iq_path_raw, NB_SAMPLES_RAW, cfg["warmup_s"], cfg["timeout_s"])
        duree_raw = round(time.time() - t0, 2)
        print(f"  → Arrêt RX (raw)...")
        stop_proc(rx_proc)
        print(f"  → Libération USRP RX ({USRP_RELEASE_S}s)...")
        time.sleep(USRP_RELEASE_S)

        print(f"  → Run 2/2 : capture CORRECTED...")
        rx_proc, iq_path_corr = launch_rx(
            cfg["rx_script"], modulation, cfg["samp_rate"],
            alpha, sps, "corrected", iq_dir, cfg["warmup_s"],
            cfg["rx_gain"], TUN_FREQ,
        )
        t0 = time.time()
        ok_corr = wait_stable_samples(iq_path_corr, NB_SAMPLES_CORR, cfg["warmup_s"], cfg["timeout_s"])
        duree_corr = round(time.time() - t0, 2)
        print(f"  → Arrêt RX (corrected)...")
        stop_proc(rx_proc)
        print(f"  → Libération USRP RX ({USRP_RELEASE_S}s)...")
        time.sleep(USRP_RELEASE_S)

        print(f"  → Arrêt TX...")
        sock.send_json({"cmd": "stop"})
        sock.recv_json()

        ts         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        debit_baud = cfg["samp_rate"] // sps

        taille_raw   = os.path.getsize(iq_path_raw)  if os.path.exists(iq_path_raw)  else 0
        taille_corr  = os.path.getsize(iq_path_corr) if os.path.exists(iq_path_corr) else 0
        nb_samp_raw  = taille_raw  // 8
        nb_samp_corr = taille_corr // 8
        nb_symb_raw  = nb_samp_raw  // sps
        nb_symb_corr = nb_samp_corr // osps_corr
        nb_bits_raw  = nb_symb_raw  * cfg["bits_par_symbole"]
        nb_bits_corr = nb_symb_corr * cfg["bits_par_symbole"]
        stat_raw     = "OK" if ok_raw  else "TIMEOUT"
        stat_corr    = "OK" if ok_corr else "TIMEOUT"

        for mode, taille, nb_samp, nb_symb, nb_bits, iq_p, duree, stat in [
            ("raw",       taille_raw,  nb_samp_raw,  nb_symb_raw,  nb_bits_raw,
             iq_path_raw,  duree_raw,  stat_raw),
            ("corrected", taille_corr, nb_samp_corr, nb_symb_corr, nb_bits_corr,
             iq_path_corr, duree_corr, stat_corr),
        ]:
            ws.append([
                ts, modulation, float(alpha), int(sps), mode,
                cfg["samp_rate"], debit_baud,
                TUN_FREQ, TX_GAIN, cfg["rx_gain"],
                cfg["warmup_s"], NB_SYMBOLES_CIBLE,
                nb_samp, nb_symb, nb_bits,
                taille, os.path.basename(iq_p),
                duree, stat,
            ])
        wb.save(EXCEL_PATH)

        if ok_raw and ok_corr:
            ok_count += 1
        print(f"  RAW       : {'✓' if ok_raw  else '✗'} {stat_raw:<7}"
              f" — {nb_samp_raw} samp | {nb_symb_raw} symb | {duree_raw}s")
        print(f"  CORRECTED : {'✓' if ok_corr else '✗'} {stat_corr:<7}"
              f" — {nb_samp_corr} samp | {nb_symb_corr} symb | {duree_corr}s")

    return ok_count, n_total


def main():
    os.makedirs(IQ_BASE_DIR, exist_ok=True)

    estimate_duration()
    input("Appuyez sur ENTRÉE pour démarrer la campagne V5... ")
    t_start = time.time()

    ctx  = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.RCVTIMEO, 30_000)
    sock.connect(f"tcp://{TX_PC_IP}:{TX_ZMQ_PORT}")
    print(f"[MASTER V5] Connexion ZMQ → {TX_PC_IP}:{TX_ZMQ_PORT}\n")

    wb, ws = init_excel(EXCEL_PATH)

    try:
        results = {}
        for modulation in MODULATION_ORDER:
            cfg = CAMPAIGN_CONFIG[modulation]
            ok_count, n_total = run_modulation_campaign(modulation, cfg, sock, wb, ws)
            results[modulation] = (ok_count, n_total)

        sock.send_json({"cmd": "quit"})
        sock.recv_json()
    except KeyboardInterrupt:
        print("\n[MASTER V5] Interruption manuelle (Ctrl+C). Envoi d'un ordre d'arrêt au TX...")
        try:
            sock.send_json({"cmd": "stop"})
            sock.recv_json()
        except Exception:
            pass
        try:
            sock.send_json({"cmd": "quit"})
            sock.recv_json()
        except Exception:
            pass
        raise
    finally:
        sock.close()
        ctx.term()

    duree_totale = time.time() - t_start
    print(f"\n{'═'*65}")
    print(f"✅  CAMPAGNE V5 TERMINÉE en {duree_totale/60:.1f} min  ({duree_totale/3600:.2f} h)")
    print(f"{'═'*65}")
    for mod, (ok, total) in results.items():
        print(f"  {mod:<6} : {ok}/{total} combinaisons entièrement réussies")
    print(f"  Excel  : {EXCEL_PATH}")
    print(f"{'═'*65}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[MASTER V5] Interruption manuelle.")
