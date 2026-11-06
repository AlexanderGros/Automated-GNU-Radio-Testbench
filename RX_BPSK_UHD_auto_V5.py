#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from packaging.version import Version as StrictVersion

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print("Warning: failed to XInitThreads()")

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import blocks
from gnuradio import digital
from gnuradio import analog
from gnuradio import gr
from gnuradio.filter import firdes
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import sys
import signal
import os
import time
import threading
import sip

IQ_DIR = r"C:\Users\Admin\Desktop\tests\IQ_V5\BPSK"

class RX_BPSK_UHD_5(gr.top_block, Qt.QWidget):

    def __init__(self, samp_rate=500000, roll_off=0.35, samples_per_symbol=4,
                 iq_dir=None, capture='raw', rx_gain=55, tun_freq=2.4e9):
        gr.top_block.__init__(self, "RX_BPSK_UHD_5", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("RX_BPSK_UHD_5")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except:
            pass
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.flowgraph_started = threading.Event()

        self.samp_rate = samp_rate
        self.iq_dir    = iq_dir if iq_dir is not None else IQ_DIR
        self.capture   = capture

        self.sps = sps = samples_per_symbol
        self.nfilts = nfilts = 32
        self.bpsk = bpsk = digital.constellation_bpsk().base()
        self.bpsk.gen_soft_dec_lut(8)
        self.alpha = alpha = roll_off
        self.tun_rx_gain = tun_rx_gain = rx_gain
        self.tun_freq = tun_freq

        self.timing_loop_bw = timing_loop_bw = 0.001
        self.phase_bw = phase_bw = 6.28 / 100.0

        self.rrc_taps = rrc_taps = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(sps), alpha, 5*sps*nfilts)
        self.num_taps = num_taps = 32
        self.fll_ntaps = fll_ntaps = 11 * sps
        self.arity = arity = 2
        self.algo = algo = digital.adaptive_algorithm_cma(bpsk, .0001, 2).base()

        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(('', "")),
            uhd.stream_args(cpu_format="fc32", args='', channels=list(range(0,1))),
        )
        self.uhd_usrp_source_0.set_subdev_spec('A:B', 0)
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(tun_freq, 180000), 0)
        self.uhd_usrp_source_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_source_0.set_gain(tun_rx_gain, 0)

        self.digital_map_bb_0 = digital.map_bb([0,1])
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, alpha, fll_ntaps, timing_loop_bw)
        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(sps, timing_loop_bw, rrc_taps, nfilts, (nfilts/2), 1.5, 2)
        self.digital_linear_equalizer_0 = digital.linear_equalizer(num_taps, 2, algo, False, [ ], '')
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(phase_bw, arity, False)
        self.digital_constellation_receiver_cb_0 = digital.constellation_receiver_cb(bpsk, timing_loop_bw, (-0.05), 0.05)
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(1)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_float*1)
        self.blocks_null_sink_char = blocks.null_sink(gr.sizeof_char*1)
        self.analog_agc2_xx_0 = analog.agc2_cc(0.0001, 0.0001, 1.0, 1.0)
        self.analog_agc2_xx_0.set_max_gain(65536)

        self.qtgui_const_sink_x_0 = qtgui.const_sink_c(
            1024,
            'BPSK Output Constellation',
            1,
            None
        )
        self.qtgui_const_sink_x_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0.set_y_axis(-2, 2)
        self.qtgui_const_sink_x_0.set_x_axis(-2, 2)
        self.qtgui_const_sink_x_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0.enable_grid(True)
        self.qtgui_const_sink_x_0.enable_axis_labels(True)
        
        self._qtgui_const_sink_x_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_const_sink_x_0_win, 0, 0, 1, 1)

        iq_path = os.path.join(self.iq_dir, f"BPSK_a{alpha:.3f}_sps{sps}_{capture}.bin")
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex * 1, iq_path, False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.iq_path = iq_path
        print(f"[RX] Mode={capture} — Fichier IQ : {iq_path}")

        self.blocks_copy_file = blocks.copy(gr.sizeof_gr_complex * 1)
        self.blocks_copy_file.set_enabled(False)

        self.connect((self.uhd_usrp_source_0, 0), (self.analog_agc2_xx_0, 0))
        self.connect((self.analog_agc2_xx_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.blocks_null_sink_char, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 1), (self.blocks_null_sink_0, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 2), (self.blocks_null_sink_0, 1))
        self.connect((self.digital_constellation_receiver_cb_0, 3), (self.blocks_null_sink_0, 2))
        self.connect((self.digital_constellation_receiver_cb_0, 4), (self.qtgui_const_sink_x_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_constellation_receiver_cb_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.digital_map_bb_0, 0))
        self.connect((self.digital_map_bb_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.digital_linear_equalizer_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_linear_equalizer_0, 0))

        if capture == 'raw':
            self.connect((self.uhd_usrp_source_0, 0), (self.blocks_copy_file, 0))
        else:
            self.connect((self.digital_constellation_receiver_cb_0, 4), (self.blocks_copy_file, 0))
        self.connect((self.blocks_copy_file, 0), (self.blocks_file_sink_0, 0))

    def closeEvent(self, event):
        self.stop()
        self.wait()
        event.accept()

def argument_parser():
    parser = ArgumentParser()
    parser.add_argument("--samp-rate", dest="samp_rate", type=eng_float, default=eng_notation.num_to_str(float(500000)))
    parser.add_argument("--roll-off", dest="roll_off", type=float, default=0.35)
    parser.add_argument("--samples-per-symbol", dest="samples_per_symbol", type=intx, default=4)
    parser.add_argument("--iq-dir", dest="iq_dir", type=str, default=None)
    parser.add_argument("--capture", dest="capture", type=str, default="raw")
    parser.add_argument("--tun-freq", dest="tun_freq", type=float, default=2.4e9)
    parser.add_argument("--rx-gain", dest="rx_gain", type=float, default=55)
    parser.add_argument("--warmup-s", dest="warmup_s", type=float, default=18.0)
    return parser

def main():
    options = argument_parser().parse_args()
    qapp = Qt.QApplication(sys.argv)
    tb = RX_BPSK_UHD_5(
        samp_rate=options.samp_rate,
        roll_off=options.roll_off,
        samples_per_symbol=options.samples_per_symbol,
        iq_dir=options.iq_dir,
        capture=options.capture,
        rx_gain=options.rx_gain,
        tun_freq=options.tun_freq,
    )

    tb.start()
    tb.flowgraph_started.set()
    tb.show()

    def _enable_file_sink():
        time.sleep(options.warmup_s)
        tb.blocks_copy_file.set_enabled(True)
        print("[RX] Warmup terminé — écriture fichier activée.")

    threading.Thread(target=_enable_file_sink, daemon=True).start()

    signal.signal(signal.SIGINT, lambda s, f: (tb.stop(), tb.wait(), Qt.QApplication.quit()))
    qapp.exec_()

if __name__ == '__main__':
    main()
