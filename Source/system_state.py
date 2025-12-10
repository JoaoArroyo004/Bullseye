class SystemState:
    def __init__(self):
        self.operation_mode = 'sleep'     # 0: sleep, 1: multiple, 2: single
        self.target_count = 0 # Current amount of targets, useful for op_mode multiple.        
        self.current_targets = ["Aa", "Bb"] # Currently being tracked
