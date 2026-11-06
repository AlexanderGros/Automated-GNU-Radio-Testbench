    cmd = [
        sys.executable, tx_script,
        "--samp-rate",          str(int(samp_rate)),
        "--roll-off",           str(alpha),
        "--samples-per-symbol", str(int(sps)),
    ]
