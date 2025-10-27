import serial.tools.list_ports
import pygame
import sys

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No controller detected.")
    sys.exit()

joy = pygame.joystick.Joystick(0)
joy.init()
print(f"Connected to: {joy.get_name()}")

while True:
    pygame.event.pump()

    print("Axes:")
    for i in range(joy.get_numaxes()):
        print(f"  Axis {i}: {joy.get_axis(i):.2f}")

    print("Buttons:")
    for i in range(joy.get_numbuttons()):
        print(f"  Button {i}: {joy.get_button(i)}")

    print("Hats:")
    for i in range(joy.get_numhats()):
        print(f"  Hat {i}: {joy.get_hat(i)}")

    print("=" * 40)
    sys.stdout.flush()
    pygame.time.wait(100)
