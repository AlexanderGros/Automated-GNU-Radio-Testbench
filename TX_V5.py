#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TX_V5.py — à lancer sur PC1 (TX)

Serveur ZMQ multi-modulation pour campagne automatique V5.
Reçoit les commandes de MASTER_CAMPAIGN (PC2) avec support optionnel 
pour l'injection de bruit et d'impraiments de canal (AWGN, frequency offset).

Dépendances : pyzmq  (pip install pyzmq)
"""

import zmq
import subprocess
import sys
import os
import time

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION — à adapter
# ══════════════════════════════════════════════════════════════════════════════
ZMQ_PORT       = 6000
USRP_RELEASE_S = 4.0

TX_SCRIPTS = {
    "BPSK":  os.path.join(os.path.dirname(__file__), "..", "TX_BPSK_UHD_auto.py"),
    "QPSK":  os.path.join(os.path.dirname(__file__), "..", "TX_QPSK_UHD_auto.py"),
    "8PSK":  os.path.join(os.path.dirname(__file__), "..", "TX_8PSK_UHD_auto.py"),
    "QAM16": os.path.join(os.path.dirname(__file__), "..", "TX_QAM16_auto.py"),
}

SAMP_RATES = {
    "BPSK":  500000,
    "QPSK":  500000,
    "8PSK":  500000,
    "QAM16": 1000000,
}
# ══════════════════════════════════════════════════════════════════════════════


def launch_tx(tx_script, samp_rate, alpha, sps, noise_voltage=0.0, freq_offset=0.0):
    """Lance le subprocess TX avec les paramètres donnés et les impaires optionnelles."""
    cmd = [
        sys.executable, tx_script,
        "--samp-rate",          str(int(samp_rate)),
        "--roll-off",           str(alpha),
        "--samples-per-symbol", str(int(sps)),
    ]
    
    # Pass optional impairment arguments if the underlying script supports them
    if noise_voltage > 0.0:
        cmd.extend(["--noise-voltage", str(noise_voltage)])
    if freq_offset != 0.0:
        cmd.extend(["--freq-offset", str(freq_offset)])

    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    print(f"  [TX] Lancement : alpha={alpha:.3f}  sps={sps}  noise_voltage={noise_voltage}  freq_offset={freq_offset}")
    return subprocess.Popen(cmd, creationflags=flags)


def stop_proc(proc):
    """Arrête proprement un subprocess GNURadio/Qt."""
    if proc is None or proc.poll() is not None:
        return
    if sys.platform == "win32":
        import signal as _signal
        try:
            os.kill(proc.pid, _signal.CTRL_BREAK_EVENT)
        except OSError:
            pass
        try:
            proc.wait(timeout=8)
            return
        except subprocess.TimeoutExpired:
            print("  [TX] CTRL_BREAK timeout → kill()")
    proc.terminate()
    try:
        proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        print("  [TX] terminate() timeout → kill()")
        proc.kill()
        proc.wait()


def boucle_zmq():
    """Ouvre le serveur ZMQ et traite les commandes start / stop / quit."""
    ctx  = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(f"tcp://0.0.0.0:{ZMQ_PORT}")
    print(f"[TX] Serveur V5 prêt sur le port {ZMQ_PORT}.")
    print(f'[TX] Protocole attendu : {{"cmd": "start", "modulation": "BPSK|QPSK|8PSK|QAM16", "alpha": float, "sps": int, "noise_voltage": float (opt), "freq_offset": float (opt)}}\n')

    tx_proc           = None
    modulation_active = None

    while True:
        msg = sock.recv_json()
        cmd = msg.get("cmd")

        if cmd == "start":
            modulation = msg.get("modulation")

            if modulation not in TX_SCRIPTS:
                err = f"modulation invalide ou absente : {modulation!r}"
                print(f"  [TX] ERREUR {err}")
                sock.send_json({"status": "error", "reason": err})
                continue

            alpha         = msg["alpha"]
            sps           = msg["sps"]
            noise_voltage = msg.get("noise_voltage", 0.0)
            freq_offset   = msg.get("freq_offset", 0.0)
            
            tx_script     = TX_SCRIPTS[modulation]
            samp_rate     = SAMP_RATES[modulation]

            if not os.path.exists(tx_script):
                err = f"script TX introuvable : {tx_script}"
                print(f"  [TX] ERREUR {err}")
                sock.send_json({"status": "error", "reason": err})
                continue

            if tx_proc is not None:
                if modulation != modulation_active:
                    print(f"  [TX] Changement modulation : {modulation_active} → {modulation}")
                stop_proc(tx_proc)
                print(f"  [TX] Libération USRP ({USRP_RELEASE_S}s)...")
                time.sleep(USRP_RELEASE_S)

            modulation_active = modulation
            tx_proc = launch_tx(tx_script, samp_rate, alpha, sps, noise_voltage, freq_offset)
            sock.send_json({"status": "ok"})

        elif cmd == "stop":
            stop_proc(tx_proc)
            tx_proc = None
            modulation_active = None
            print(f"  [TX] Libération USRP ({USRP_RELEASE_S}s)...")
            time.sleep(USRP_RELEASE_S)
            print("  [TX] Arrêté.")
            sock.send_json({"status": "ok"})

        elif cmd == "quit":
            stop_proc(tx_proc)
            sock.send_json({"status": "ok"})
            print("[TX] Fin de campagne.")
            break

        else:
            print(f"  [TX] Commande inconnue : {cmd!r}")
            sock.send_json({"status": "error", "reason": f"commande inconnue : {cmd!r}"})

    sock.close()
    ctx.term()


def main():
    boucle_zmq()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[TX] Interruption.")
