class ControlProcessor:
    def __init__(self):
        self.steering = 0.0
        self.throttle = 0.0

        self.max_steering = 0.5   # rad
        self.max_speed = 2.0      # m/s

    def process(self, control):
        x, y = control

        # steering (angular)
        steering = x * self.max_steering

        # throttle (linear)
        throttle = y * self.max_speed

        self.steering = steering
        self.throttle = throttle

        return steering, throttle