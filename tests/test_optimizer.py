import unittest
from src.optimizer import optimize_battery

class TestOptimizer(unittest.TestCase):
    def obs(self, soc=1000, prices=None, co2=None):
        return {'soc_kwh': soc, 'preus_properes_24h': prices or [0.1]*24,
                'co2_properes_24h': co2 or [0.2]*24,
                'noves_dades_5min': {'ultim_consum_kw': 800, 'ultima_solar_kw': 100}}

    def test_safe_at_empty(self):
        self.assertGreaterEqual(optimize_battery(self.obs(soc=0)), 0)

    def test_safe_at_full(self):
        self.assertLessEqual(optimize_battery(self.obs(soc=2000)), 0)

    def test_power_limit(self):
        self.assertLessEqual(abs(optimize_battery(self.obs())), 500)

    def test_price_shift(self):
        prices = [0.01] + [0.3]*23
        self.assertGreater(optimize_battery(self.obs(prices=prices)), 0)

if __name__ == '__main__':
    unittest.main()
