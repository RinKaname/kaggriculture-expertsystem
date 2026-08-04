import math
from src.constants import CROPS, hire_cost, MOVES
from src.pathfinding import manhattan_distance, plan_manhattan_path, solve_tsp_nearest_neighbor


class WorkerManager:
    def __init__(self):
        self.current_day = -1
        self.worker_schedules = []  # List of action queues, one per unit (farmer + hands)
        self.planned_hires_today = 0

    def start_new_day(self, obs, player_id, planned_plants=None):
        """Analyze farm state, determine hires, and build 24-turn schedules for all workers."""
        farm = obs["farms"][player_id]
        private = obs["private"]
        day = obs.get("day", 0)
        money = farm["money"]
        board_size = len(farm["tiles"])
        
        self.current_day = day
        planned_plants = planned_plants or []  # list of (x, y, crop)

        # 1. Gather all tasks
        harvest_tasks = []
        water_tasks = []
        dig_tasks = []
        plant_tasks = []

        for y in range(board_size):
            for x in range(board_size):
                tile = farm["tiles"][y][x]
                if tile == "LOCKED":
                    continue
                if tile is None:
                    continue
                if isinstance(tile, dict):
                    kind = tile.get("kind")
                    if kind == "WEED":
                        dig_tasks.append(((x, y), ["DIG"]))
                    elif kind == "PLANT":
                        crop = tile["crop"]
                        cd = CROPS[crop]
                        age = day - tile["planted_day"]
                        
                        # Check harvest conditions
                        should_harvest = False
                        if cd["ongoing"]:
                            if tile.get("yield_units", 0) > 0:
                                should_harvest = True
                        else:
                            # Harvest if max_yield_day reached or end of season
                            if age >= cd["max_yield_day"] or (day >= 28 and age >= cd["first_yield_day"]):
                                should_harvest = True

                        if should_harvest:
                            harvest_tasks.append(((x, y), ["HARVEST"]))
                        elif not tile["watered_today"]:
                            water_tasks.append(((x, y), ["WATER"]))

        for (x, y, crop) in planned_plants:
            plant_tasks.append(((x, y), ["PLANT", crop]))

        # High priority: Harvest first, then Water, then Dig, then Plant
        all_tasks = harvest_tasks + water_tasks + dig_tasks + plant_tasks
        total_tasks = len(all_tasks)

        # 2. Determine Hires
        # Each worker can comfortably complete 12 tasks per day.
        needed_workers = max(1, math.ceil(total_tasks / 12.0))
        target_hires = needed_workers - 1

        # Budget check for hires
        actual_hires = 0
        cumulative_hire_cost = 0
        for h in range(target_hires):
            cost = hire_cost(h)
            if cumulative_hire_cost + cost <= money - 50:  # keep buffer for seeds
                cumulative_hire_cost += cost
                actual_hires += 1
            else:
                break

        self.planned_hires_today = actual_hires
        total_active_workers = 1 + actual_hires

        # 3. Partition tasks among workers
        # Sort tasks spatially (e.g. by y * board_size + x)
        all_tasks.sort(key=lambda t: t[0][1] * board_size + t[0][0])
        
        worker_task_bins = [[] for _ in range(total_active_workers)]
        for idx, task in enumerate(all_tasks):
            bin_idx = idx % total_active_workers
            worker_task_bins[bin_idx].append(task)

        # 4. Generate action schedule for each worker
        self.worker_schedules = []
        spawn_pos = tuple(farm["farmer"])

        for w_idx in range(total_active_workers):
            tasks_for_w = worker_task_bins[w_idx]
            # Order tasks using TSP
            ordered_tasks = solve_tsp_nearest_neighbor(spawn_pos, tasks_for_w)
            
            # Convert to sequence of per-turn commands (up to 24 turns)
            schedule = []
            curr_pos = list(spawn_pos)
            
            for (target_pos, op) in ordered_tasks:
                if len(schedule) >= 24:
                    break
                # Movement path
                moves = plan_manhattan_path(curr_pos, target_pos)
                for m in moves:
                    if len(schedule) >= 24:
                        break
                    schedule.append([m])
                    dx, dy = MOVES[m]
                    curr_pos[0] += dx
                    curr_pos[1] += dy
                
                # Perform the operation
                if len(schedule) < 24:
                    schedule.append(op)

            # Pad remaining turns with PASS
            while len(schedule) < 24:
                schedule.append(["PASS"])

            self.worker_schedules.append(schedule)

    def get_actions_for_turn(self, hour):
        """Get the action for farmer and all hands for the current hour (0-23)."""
        farmer_act = ["PASS"]
        hands_acts = []
        
        if self.worker_schedules and len(self.worker_schedules) > 0:
            if hour < len(self.worker_schedules[0]):
                farmer_act = self.worker_schedules[0][hour]

        for h_idx in range(1, len(self.worker_schedules)):
            if hour < len(self.worker_schedules[h_idx]):
                hands_acts.append(self.worker_schedules[h_idx][hour])
            else:
                hands_acts.append(["PASS"])

        return farmer_act, hands_acts
