"""Optimitzador MPC de bateria per al repte UPC.

Interfície independent: optimize_battery(obs, load_forecast=None, pv_forecast=None).
No utilitza dades futures reals de demanda/solar.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

CAPACITY_KWH = 2000.0
MAX_POWER_KW = 500.0
ETA = 0.9 ** 0.5


def optimize_battery(obs: dict, load_forecast=None, pv_forecast=None,
                     reference_cost_per_hour=100.0,
                     reference_co2_per_hour=150.0,
                     terminal_weight=0.15) -> float:
    """Retorna la consigna segura (kW): positiva carrega, negativa descarrega.

    Si no es proporcionen prediccions, manté constant la darrera demanda i
    aplica una aproximació solar conservadora (última potència mesurada).
    Les referències de cost/CO2 s'han de calibrar amb dades de train.
    """
    prices = np.asarray(obs['preus_properes_24h'], dtype=float)
    co2 = np.asarray(obs['co2_properes_24h'], dtype=float)
    n = min(len(prices), len(co2), 24)
    if n == 0:
        return 0.0
    prices, co2 = prices[:n], co2[:n]
    if not np.isfinite(prices).all() or not np.isfinite(co2).all():
        return 0.0
    last = obs['noves_dades_5min']

    def forecast(values, fallback):
        if values is None:
            return np.full(n, max(0.0, float(fallback)))
        a = np.asarray(values, dtype=float).reshape(-1)
        if len(a) < n or not np.isfinite(a[:n]).all():
            raise ValueError('La previsió ha de contenir n valors finits')
        return np.maximum(a[:n], 0.0)

    load = forecast(load_forecast, last['ultim_consum_kw'])
    pv = forecast(pv_forecast, last['ultima_solar_kw'])
    net = load - pv
    soc = float(obs['soc_kwh'])
    if not np.isfinite(soc):
        return 0.0
    soc = np.clip(soc, 0.0, CAPACITY_KWH)

    # Variables: [charge(n), discharge(n), grid_import(n), stored_energy(n)]
    # No s'atribueix benefici per exportació: el simulador local usa 0 €/kWh.
    m = 4 * n
    charge, discharge, grid, energy = 0, n, 2*n, 3*n
    weights = 0.7 * co2 / max(reference_co2_per_hour, 1e-9) + \
              0.3 * prices / max(reference_cost_per_hour, 1e-9)
    obj = np.zeros(m)
    obj[grid:grid+n] = weights
    # Petita penalització al throughput per evitar càrrega i descàrrega simultànies.
    throughput_penalty = max(1e-8, 1e-5 * np.mean(np.abs(weights)))
    obj[charge:charge+n] = throughput_penalty
    obj[discharge:discharge+n] = throughput_penalty
    # Valor residual d'energia per evitar descarregar-ho tot al final de l'horitzó.
    obj[energy+n-1] = -terminal_weight * max(0.0, np.mean(weights)) * ETA

    aeq = np.zeros((n, m))
    beq = np.zeros(n)
    for t in range(n):
        aeq[t, energy+t] = 1
        aeq[t, charge+t] = -ETA
        aeq[t, discharge+t] = 1 / ETA
        if t:
            aeq[t, energy+t-1] = -1
        else:
            beq[t] = soc

    # grid_import >= net + charge - discharge
    aub = np.zeros((n, m))
    bub = -net.copy()
    for t in range(n):
        aub[t, charge+t] = 1
        aub[t, discharge+t] = -1
        aub[t, grid+t] = -1

    bounds = ([(0, MAX_POWER_KW)] * (2*n) +
              [(0, None)] * n + [(0, CAPACITY_KWH)] * n)
    result = linprog(obj, A_ub=aub, b_ub=bub, A_eq=aeq,
                     b_eq=beq, bounds=bounds, method='highs')
    if not result.success:
        return 0.0
    action = float(result.x[charge] - result.x[discharge])
    # Marges de seguretat contra clipping per errors de coma flotant.
    eps = 1e-5
    upper = max(0.0, min(MAX_POWER_KW, (CAPACITY_KWH - soc) / ETA - eps))
    lower = max(0.0, min(MAX_POWER_KW, soc * ETA - eps))
    return float(np.clip(action, -lower, upper))
