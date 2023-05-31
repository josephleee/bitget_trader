from modules.rsi_module import RsiAlgorithm

if __name__ == '__main__':
    a = RsiAlgorithm(candle_range='1d')
    a.run()