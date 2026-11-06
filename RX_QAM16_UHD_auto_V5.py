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
from gnuradio.filter import firdes
import sip
from gnuradio import blocks
from gnuradio import digital
from gnuradio import analog
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
import os
import threading
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
from gnuradio.qtgui import Range, RangeWidget
from PyQt5 import QtCore

class RX_QAM16_UHD_5(gr.top_block, Qt.QWidget):

    def __init__(self, samp_rate=1000000, roll_off=0.35, samples_per_symbol=4,
                 iq_dir=None, capture='raw', rx_gain=55, tun_freq=2.4e9):
        gr.top_block.__init__(self, "RX_QAM16_UHD_5", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("RX_QAM16_UHD_5")
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

        self.settings = Qt.QSettings("GNU Radio", "RX_QAM16_UHD_5")

        try:
            if StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
                self.restoreGeometry(self.settings.value("geometry").toByteArray())
            else:
                self.restoreGeometry(self.settings.value("geometry"))
        except:
            pass

        self.flowgraph_started = threading.Event()

        self.samp_rate = samp_rate
        self.iq_dir    = iq_dir if iq_dir is not None else os.path.dirname(os.path.abspath(__file__))
        self.capture   = capture

        self.sps = sps = samples_per_symbol
        self.nfilts = nfilts = 64
        self.const = const = digital.constellation_16qam().base()
        self.const.gen_soft_dec_lut(8)
        self.alpha = alpha = roll_off
        self.tun_rx_gain = tun_rx_gain = rx_gain
        self.tun_freq = tun_freq
        
        self.timing_loop_bw = timing_loop_bw = (6.28 / 100.0) / float(sps)
        self.fll_loop_bw = fll_loop_bw = 0.001
        self.rx_loop_bw = rx_loop_bw = (6.28 / 100.0) / float(sps)
        
        self.rrc_taps = rrc_taps = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(sps), alpha, 5*sps*nfilts)
        self.num_taps = num_taps = 32
        self.fll_ntaps = fll_ntaps = 11 * sps
        self.init_phase = init_phase = nfilts/2
        self.arity = arity = 16
        self.algo = algo = digital.adaptive_algorithm_cma(const, .0001, 2).base()

        self.controls = Qt.QTabWidget()
        self.controls_widget_0 = Qt.QWidget()
        self.controls_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.controls_widget_0)
        self.controls_grid_layout_0 = Qt.QGridLayout()
        self.controls_layout_0.addLayout(self.controls_grid_layout_0)
        self.controls.addTab(self.controls_widget_0, 'Channel')
        self.controls_widget_1 = Qt.QWidget()
        self.controls_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.controls_widget_1)
        self.controls_grid_layout_1 = Qt.QGridLayout()
        self.controls_layout_1.addLayout(self.controls_grid_layout_1)
        self.controls.addTab(self.controls_widget_1, 'Receiver')
        self.top_grid_layout.addWidget(self.controls, 0, 0, 1, 2)

        self.uhd_usrp_source_1 = uhd.usrp_source(
            ",".join(('', '')),
            uhd.stream_args(cpu_format="fc32", args='', channels=list(range(0,1))),
        )
        self.uhd_usrp_source_1.set_subdev_spec('A:B', 0)
        self.uhd_usrp_source_1.set_samp_rate(samp_rate)
        self.uhd_usrp_source_1.set_time_unknown_pps(uhd.time_spec(0))
        self.uhd_usrp_source_1.set_center_freq(uhd.tune_request(tun_freq), 0)
        self.uhd_usrp_source_1.set_antenna("TX/RX", 0)
        self.uhd_usrp_source_1.set_gain(tun_rx_gain, 0)

        self.analog_agc2_xx_0 = analog.agc2_cc(0.0001, 0.0001, 1.0, 1.0)
        self.analog_agc2_xx_0.set_max_gain(65536)

        self.qtgui_time_sink_x_2 = qtgui.time_sink_c(1024, samp_rate, 'Received signal', 1, None)
        self.qtgui_time_sink_x_0 = qtgui.time_sink_f(500, samp_rate, '', 1, None)
        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_c(1024, window.WIN_BLACKMAN_hARRIS, 2400000000, samp_rate, "", 1, None)
        self.qtgui_eye_sink_x_1 = qtgui.eye_sink_c(1024, samp_rate, 1, None)
        self.qtgui_eye_sink_x_0 = qtgui.eye_sink_f(1024, samp_rate, 1, None)
        self.qtgui_const_sink_x_0_1_0 = qtgui.const_sink_c(1024, 'Received constellation', 1, None)
        
        self.qtgui_const_sink_x_0_1 = qtgui.const_sink_c(1024, 'QAM16 Output Constellation', 1, None)
        self.qtgui_const_sink_x_0_1.set_update_time(0.10)
        self.qtgui_const_sink_x_0_1.set_y_axis(-2, 2)
        self.qtgui_const_sink_x_0_1.set_x_axis(-2, 2)
        self.qtgui_const_sink_x_0_1.enable_autoscale(False)
        self.qtgui_const_sink_x_0_1.enable_grid(True)
        self.qtgui_const_sink_x_0_1.enable_axis_labels(True)
        
        self._qtgui_const_sink_x_0_1_win = sip.wrapinstance(self.qtgui_const_sink_x_0_1.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_const_sink_x_0_1_win, 1, 0, 1, 2)

        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(sps, timing_loop_bw, rrc_taps, nfilts, init_phase, 1.5, 2)
        self.digital_map_bb_0 = digital.map_bb([0,1,2,3])
        self.digital_linear_equalizer_0 = digital.linear_equalizer(num_taps, 2, algo, False, [ ], '')
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, alpha, fll_ntaps, fll_loop_bw)
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.digital_constellation_receiver_cb_0 = digital.constellation_receiver_cb(const, rx_loop_bw, (-0.2), 0.2)
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(2)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_float*1)
        self.blocks_char_to_float_0_0_0 = blocks.char_to_float(1, 1)
        self.blocks_char_to_float_0_0 = blocks.char_to_float(1, 1)

        iq_path = os.path.join(self.iq_dir, f"QAM16_a{alpha:.3f}_sps{sps}_{capture}.bin")
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex * 1, iq_path, False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.iq_path = iq_path
        print(f"[RX] Mode={capture} — Fichier IQ : {iq_path}")

        self.blocks_copy_file = blocks.copy(gr.sizeof_gr_complex * 1)
        self.blocks_copy_file.set_enabled(False)

        self.connect((self.blocks_char_to_float_0_0, 0), (self.qtgui_eye_sink_x_0, 0))
        self.connect((self.blocks_char_to_float_0_0_0, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.uhd_usrp_source_1, 0), (self.analog_agc2_xx_0, 0))
        self.connect((self.analog_agc2_xx_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.analog_agc2_xx_0, 0), (self.qtgui_const_sink_x_0_1_0, 0))
        self.connect((self.analog_agc2_xx_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.blocks_char_to_float_0_0_0, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 0), (self.blocks_char_to_float_0_0, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 1), (self.blocks_null_sink_0, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 2), (self.blocks_null_sink_0, 1))
        self.connect((self.digital_constellation_receiver_cb_0, 3), (self.blocks_null_sink_0, 2))
        self.connect((self.digital_constellation_receiver_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 4), (self.qtgui_const_sink_x_0_1, 0))
        self.connect((self.digital_constellation_receiver_cb_0, 4), (self.qtgui_eye_sink_x_1, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.digital_map_bb_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_linear_equalizer_0, 0))
        self.connect((self.digital_linear_equalizer_0, 0), (self.digital_constellation_receiver_cb_0, 0))
        self.connect((self.digital_map_bb_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.uhd_usrp_source_1, 0), (self.qtgui_time_sink_x_2, 0))

        if capture == 'raw':
            self.connect((self.uhd_usrp_source_1, 0), (self.blocks_copy_file, 0))
        else:
            self.connect((self.digital_constellation_receiver_cb_0, 4), (self.blocks_copy_file, 0))
        self.connect((self.blocks_copy_file, 0), (self.blocks_file_sink_0, 0))

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "RX_QAM16_UHD_5")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()
        event.accept()

def argument_parser():
    parser = ArgumentParser()
    parser.add_argument("--samp-rate", dest="samp_rate", type=eng_float, default=eng_notation.num_to_str(float(1000000)))
    parser.add_argument("--roll-off", dest="roll_off", type=float, default=0.35)
    parser.add_argument("--samples-per-symbol", dest="samples_per_symbol", type=intx, default=4)
    parser.add_argument("--iq-dir", dest="iq_dir", type=str, default=None)
    parser.add_argument("--capture", dest="capture", type=str, default="raw")
    parser.add_argument("--tun-freq", dest="tun_freq", type=float, default=2.4e9)
    parser.add_argument("--rx-gain", dest="rx_gain", type=float, default=55)
    parser.add_argument("--warmup-s", dest="warmup_s", type=float, default=18.0)
    return parser

def main(top_block_cls=RX_QAM16_UHD_5, options=None):
    if options is None:
        options = argument_parser().parse_args()
    qapp = Qt.QApplication(sys.argv)
    tb = top_block_cls(
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

    def _enable_file_sink():
        time.sleep(options.warmup_s)
        tb.blocks_copy_file.set_enabled(True)

    threading.Thread(target=_enable_file_sink, daemon=True).start()
    tb.show()
    signal.signal(signal.SIGINT, lambda s, f: (tb.stop(), tb.wait(), Qt.QApplication.quit()))
    qapp.exec_()

if __name__ == '__main__':
    main()
