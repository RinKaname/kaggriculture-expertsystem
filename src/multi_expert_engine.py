"""Multi-Expert Rule-Based Engine Suite for Kaggriculture.
Houses the 5 distinct Grandmaster Strategy Archetypes + Front-Running Interceptor.
"""
import copy
import json
import os
import sys

# Ensure root directory is accessible for imports
_SRC_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "src")
_ROOT_DIR = os.path.abspath(os.path.join(_SRC_DIR, '..'))
sys.path.append(_ROOT_DIR)

from src.baseline import ApexGrandmasterAgent
from src.subin_an_tape import agent as subin_agent

# Load decrypted 720-step Elite Grandmaster Trace
_TRACE = []
trace_path = os.path.abspath(os.path.join(_ROOT_DIR, 'decompressed_trace.json'))

if os.path.exists(trace_path):
    with open(trace_path, 'r', encoding='utf-8') as f:
        _TRACE = json.load(f)
else:
    import main as elite_main
    _TRACE = getattr(elite_main, 'TRACE_ACTIONS', [])

_SELLABLE = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
_FRONT_RUN_ITEMS = ["MELON", "MILK", "WOOL", "STRAWBERRY", "TOMATO"]
_BASE_PRICE = {
    "WHEAT": 10, "CARROT": 15, "TOMATO": 14, "STRAWBERRY": 24, "MELON": 55,
    "EGG": 12, "MILK": 42, "WOOL": 70, "FERTILIZER": 0
}
_GLUT_WEIGHT = {
    "MELON": 2.5, "MILK": 2.2, "WOOL": 2.2, "STRAWBERRY": 1.8, "TOMATO": 1.4,
    "WHEAT": 0.5, "CARROT": 0.8, "EGG": 1.0, "FERTILIZER": 0.1
}



class MultiExpertSystem:
    """
    Unified Multi-Expert Execution Engine.
    Houses the top Grandmaster Meta-Archetypes:
    0: META_ELITE_TAPE (VN-Orion $182k Solved Trajectory)
    1: META_SUBIN_MOON_V14 (Subin An 629/644 Win Grandmaster Policy)
    2: META_MELON_IPO (16 Melons Day 0-9 Early Cash Blitz)
    3: META_COW_RANCH (10 Cows Pure Rancher NE Quadrant)
    4: META_FRUIT_ENGINE (Strawberries + Tomatoes Continuous Harvest)
    5: COUNTER_FRONT_RUN (Elite Tape + Force Proactive Front-Running)
    6: PANIC_LIQUIDATION (Forces Shed Dump)
    """

    def __init__(self):
        # Expert 2: Melon IPO Blitz Engine
        self.melon_ipo_expert = ApexGrandmasterAgent()
        self.melon_ipo_expert.p.update({
            "melon_target": 16,
            "melon_cutoff_day": 10,
            "strawberry_start_day": 30,
            "max_cows": 2,
            "max_sheep": 0,
            "sell_thresh": 0.50
        })

        # Expert 3: Cow Rancher Surge Engine
        self.cow_ranch_expert = ApexGrandmasterAgent()
        self.cow_ranch_expert.p.update({
            "max_cows": 10,
            "max_sheep": 0,
            "melon_target": 0,
            "melon_cutoff_day": 0,
            "strawberry_start_day": 30,
            "quad2_day_cutoff": 4,
            "animal_min_cash": 600
        })

        # Expert 4: Fruit & Continuous Harvest Engine
        self.fruit_expert = ApexGrandmasterAgent()
        self.fruit_expert.p.update({
            "max_cows": 4,
            "max_sheep": 2,
            "straw_target": 12,
            "strawberry_start_day": 3,
            "melon_cutoff_day": 6,
            "sell_thresh": 0.60,
            "milk_wool_thresh": 0.50
        })

        self.last_step = -1
        self.clone_confidence = 0

    def reset(self):
        self.last_step = -1
        self.clone_confidence = 0
        self.melon_ipo_expert = ApexGrandmasterAgent()
        self.melon_ipo_expert.p.update({
            "melon_target": 16,
            "melon_cutoff_day": 10,
            "strawberry_start_day": 30,
            "max_cows": 2,
            "max_sheep": 0,
            "sell_thresh": 0.50
        })
        self.cow_ranch_expert = ApexGrandmasterAgent()
        self.cow_ranch_expert.p.update({
            "max_cows": 10,
            "max_sheep": 0,
            "melon_target": 0,
            "melon_cutoff_day": 0,
            "strawberry_start_day": 30,
            "quad2_day_cutoff": 4,
            "animal_min_cash": 600
        })
        self.fruit_expert = ApexGrandmasterAgent()
        self.fruit_expert.p.update({
            "max_cows": 4,
            "max_sheep": 2,
            "straw_target": 12,
            "strawberry_start_day": 3,
            "melon_cutoff_day": 6,
            "sell_thresh": 0.60,
            "milk_wool_thresh": 0.50
        })

    def _execute_elite_tape(self, obs, force_front_run=False):
        """Executes the $182k solved Grandmaster Tape (Cluster E)."""
        step = min(int(obs.get("step", 0) or 0), len(_TRACE) - 1)
        
        # Terminal endgame phase (steps 717-719)
        if step >= 717:
            return self._terminal_action(obs)

        action = copy.deepcopy(_TRACE[step]) if step < len(_TRACE) else {"farmer": ["PASS"], "hands": [], "market": []}

        # Front-running interception
        self._apply_front_running(action, obs, step, force=force_front_run)

        # Terminal liquidation safeguard
        if step >= 710:
            self._apply_panic_sell(action, obs)
        return action

    def _terminal_action(self, obs):
        """Final turns fallback and complete shed dump."""
        player = obs.get("player", 0)
        farm = (obs.get("farms") or [{}])[player]
        hands_count = len(farm.get("hands", []))
        action = {
            "farmer": ["PASS"],
            "hands": [["PASS"] for _ in range(hands_count)],
            "market": []
        }
        self._apply_panic_sell(action, obs)
        return action


    def _apply_front_running(self, action, obs, step, force=False):
        """Forces sell of premium goods 1 step ahead of predicted market gluts."""
        orders = list(action.get("market", []) or [])
        if len(orders) >= 10:
            return
        already = {}
        for order in orders:
            if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL":
                already[order[1]] = already.get(order[1], 0) + max(0, int(order[2] or 0))
        
        planned = {}
        end = min(len(_TRACE), step + 2)
        for future_step in range(step + 1, end):
            distance = future_step - step
            for order in _TRACE[future_step].get("market", []) or []:
                if not (
                    isinstance(order, list) and len(order) >= 3
                    and order[0] == "SELL" and order[1] in _FRONT_RUN_ITEMS
                ):
                    continue
                item = order[1]
                quantity = max(0, int(order[2] or 0))
                if item not in planned:
                    planned[item] = [distance, quantity]
                else:
                    planned[item][1] += quantity

        shed = (obs.get("private") or {}).get("shed") or {}
        prices = ((obs.get("market") or {}).get("prices") or {})
        choices = []
        for item, (distance, quantity) in planned.items():
            available = max(0, int(shed.get(item, 0) or 0) - already.get(item, 0))
            quantity = min(available, quantity if not force else max(quantity, available))
            if quantity <= 0:
                continue
            price = float(prices.get(item, _BASE_PRICE[item]) or 0)
            priority = price * quantity * _GLUT_WEIGHT[item] + (2 - distance) * _BASE_PRICE[item]
            choices.append((priority, item, quantity))

        if choices:
            _, item, quantity = max(choices)
            orders.append(["SELL", item, quantity])
            action["market"] = orders[:10]

    def _apply_panic_sell(self, action, obs):
        """Dumps all sellable items in the shed immediately."""
        private = obs.get("private") or {}
        shed = private.get("shed") or {}
        orders = list(action.get("market", []) or [])
        already_selling = {
            o[1] for o in orders if isinstance(o, list) and len(o) >= 2 and o[0] == "SELL"
        }
        for item in _SELLABLE:
            qty = int(shed.get(item, 0) or 0)
            if qty > 0 and item not in already_selling and len(orders) < 10:
                orders.append(["SELL", item, qty])
        action["market"] = orders[:10]

    def act(self, obs, macro_action=0):
        """
        Routes the observation to the selected Rule-Based Expert System:
        0: META_ELITE_TAPE (VN-Orion $182k Solved Trajectory)
        1: META_SUBIN_MOON_V14 (Subin An 629/644 Win Policy)
        2: META_MELON_IPO (16 Melons Day 0-9 Early Cash Blitz)
        3: META_COW_RANCH (10 Cows Pure Rancher NE Quadrant)
        4: META_FRUIT_ENGINE (Strawberries + Tomatoes Continuous Harvest)
        5: COUNTER_FRONT_RUN (Elite Tape + Force Proactive Front-Running)
        6: PANIC_LIQUIDATION (Forces Shed Dump)
        """
        step = int(obs.get("step", 0) or 0)
        self.last_step = step

        if macro_action == 0:
            return self._execute_elite_tape(obs, force_front_run=False)
        elif macro_action == 1:
            return subin_agent(obs)
        elif macro_action == 2:
            return self.melon_ipo_expert.act(obs)
        elif macro_action == 3:
            return self.cow_ranch_expert.act(obs)
        elif macro_action == 4:
            return self.fruit_expert.act(obs)
        elif macro_action == 5:
            return self._execute_elite_tape(obs, force_front_run=True)
        elif macro_action == 6:
            action = self._execute_elite_tape(obs, force_front_run=False)
            self._apply_panic_sell(action, obs)
            return action
        else:
            return self._execute_elite_tape(obs, force_front_run=False)

