"""Comparació local de baseline oficial i MPC, sense modificar agent.py."""
from pathlib import Path
import sys
import importlib.util
import time
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from starter_kit.environment import run_agent_simulation
from src.optimizer import optimize_battery


def load_class(path):
    spec = importlib.util.spec_from_file_location('baseline_official', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BatteryAgent


def read_series(filename, column=None):
    df = pd.read_csv(ROOT / 'data' / 'train' / filename, parse_dates=['Fecha']).set_index('Fecha')
    if column is None:
        columns = [c for c in df.columns if 'POTENCIA ACTIVA' in c and 'FASE' not in c]
        if not columns:
            raise ValueError('No s’han trobat columnes dels inversors')
        series = df[columns].sum(axis=1).clip(lower=0)
    else:
        series = pd.to_numeric(df[column], errors='coerce')
    return series.resample('1h').mean()


def prepare_data():
    load = -read_series('contador.csv', 'Contador - POTENCIA ACTIVA EXPORTADA (kW)')
    load = load.clip(lower=0, upper=5000)
    pv = read_series('inversor.csv')
    price = read_series('precio_pvpc.csv', 'precio_eur_per_kwh')
    co2 = read_series('co2_red.csv', 'co2_kg_per_kwh')
    df = pd.DataFrame({'load_kw': load, 'pv_kw': pv,
                       'precio_eur_per_kwh': price, 'co2_kg_per_kwh': co2}).dropna().sort_index()
    if df.empty:
        raise ValueError('No hi ha hores coincidents entre els quatre fitxers')
    return df


class MPCAgent:
    def act(self, obs):
        return optimize_battery(obs)


def main():
    df = prepare_data()
    # Mateix període per als dos agents, amb estat inicial reiniciat.
    # Primeres 168 hores per a una prova ràpida; passar 2016 com argument.
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 168
    sample = df.iloc[:hours]
    print(f'Hores disponibles: {len(df)}; hores de prova: {len(sample)}')
    baseline = load_class(ROOT / 'starter_kit' / 'agent.py')
    for name, agent in [('Baseline oficial', baseline()), ('MPC', MPCAgent())]:
        start = time.perf_counter()
        result = run_agent_simulation(agent, sample)
        print(f'\n{name}: {result}\nTemps: {time.perf_counter()-start:.2f}s')


if __name__ == '__main__':
    main()
