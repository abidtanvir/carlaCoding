import carla
import pygame
import numpy as np
import time
from agents.navigation.basic_agent import BasicAgent

# Server details
CARLA_SERVER_HOST = "ce-gpu.informatik.tu-chemnitz.de"
CARLA_SERVER_PORT = 2110

# Pygame display dimensions
display_width = 1000
display_height = 800

def carla_image_to_pygame(image):
    """Convert CARLA camera image to Pygame format."""
    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = array.reshape((image.height, image.width, 4))  # BGRA format
    array = array[:, :, :3]  # Take RGB channels only
    array = array[:, :, ::-1]  # Convert from BGR to RGB
    return array

def spawn_traffic_cars(world, blueprint_library, num_cars=20):
    """Spawn diverse traffic vehicles including cars, buses, and motorbikes."""
    traffic_cars = []
    vehicle_types = ['vehicle.audi.tt', 'vehicle.tesla.model3', 'vehicle.carlamotors.carlacola',
                     'vehicle.mini.cooper_s', 'vehicle.dodge.charger_police', 'vehicle.harley-davidson.low_rider']

    spawn_points = world.get_map().get_spawn_points()
    for i in range(num_cars):
        spawn_point = spawn_points[i % len(spawn_points)]
        vehicle_bp = blueprint_library.find(np.random.choice(vehicle_types))  # Randomly pick vehicle type
        vehicle = world.try_spawn_actor(vehicle_bp, spawn_point)
        if vehicle:
            traffic_cars.append(vehicle)
            vehicle.set_autopilot(True)  # Enable autopilot for traffic cars
            print(f"Spawned {vehicle_bp.id} at {spawn_point.location}")
        else:
            print("Failed to spawn a traffic vehicle.")
    return traffic_cars

def setup_traffic_lights(world):
    """Setup and activate traffic lights."""
    traffic_lights = []
    for light in world.get_actors().filter('traffic.traffic_light'):
        light.set_state(carla.TrafficLightState.Red)  # Initially set all lights to RED
        light.set_green_time(5.0)  # Set green light duration
        light.set_red_time(5.0)    # Set red light duration
        traffic_lights.append(light)
        print(f"Traffic light added at {light.get_transform().location}")
    return traffic_lights

def main():
    pygame.init()
    display = pygame.display.set_mode((display_width, display_height), pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.display.set_caption("CARLA Simulation")
    clock = pygame.time.Clock()

    traffic_cars = []  # Initialize traffic_cars to avoid reference errors
    camera = None
    vehicle = None
    bus = None

    try:
        # Connect to CARLA server
        client = carla.Client(CARLA_SERVER_HOST, CARLA_SERVER_PORT)
        client.set_timeout(10.0)

        # Load a specific town
        town_name = "Town03"
        print(f"Loading town: {town_name}")
        client.load_world(town_name)
        world = client.get_world()

        # Allow time for the world to load
        time.sleep(2)

        # Get spawn points and define start and endpoint
        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            print("No spawn points available!")
            return

        start_point = spawn_points[0]  # First spawn point as start
        endpoint_location = carla.Location(x=start_point.location.x + 115,
                                           y=start_point.location.y + 135,
                                           z=start_point.location.z)
        print(f"Start Point: {start_point.location}")
        print(f"Endpoint: {endpoint_location}")

        # Get the blueprint library
        blueprint_library = world.get_blueprint_library()

        # Spawn the main vehicle at the start point
        vehicle_bp = blueprint_library.find('vehicle.tesla.model3')
        vehicle = world.try_spawn_actor(vehicle_bp, start_point)
        if vehicle is None:
            print("Failed to spawn the main vehicle!")
            return
        print(f"Main vehicle spawned at {start_point.location}")

        # Instead of keeping the car stationary, we will control it with the BasicAgent.
        # First, let's set up the camera.
        camera_bp = blueprint_library.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', str(display_width))
        camera_bp.set_attribute('image_size_y', str(display_height))
        camera_bp.set_attribute('fov', '90')

        camera_transform = carla.Transform(carla.Location(x=130, y=-65, z=210), carla.Rotation(pitch=-90))
        camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)

        latest_image = None
        def process_image(image):
            nonlocal latest_image
            latest_image = image

        camera.listen(lambda image: process_image(image))

        # Visualize the endpoint with a large bus
        bus_bp = blueprint_library.find('vehicle.carlamotors.carlacola')  # Using a bus as the marker
        bus_transform = carla.Transform(endpoint_location)
        bus = world.try_spawn_actor(bus_bp, bus_transform)
        if bus:
            print(f"Endpoint marker (bus) spawned at {endpoint_location}")
            print(f"Absolute Endpoint Location: {endpoint_location}")
        else:
            print("Failed to spawn the endpoint marker.")

        # Setup traffic lights
        traffic_lights = setup_traffic_lights(world)

        # Spawn additional traffic cars
        traffic_cars = spawn_traffic_cars(world, blueprint_library, num_cars=10)

        # NEW: Use BasicAgent for the main vehicle
        agent = BasicAgent(vehicle)  # <-- NEW
        # Set the destination for the agent. It expects a carla.Location or a waypoint.
        agent.set_destination(endpoint_location)  # <-- NEW

        # Main loop
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

            # NEW: Let the agent compute the next control step
            control = agent.run_step()  # <-- NEW
            vehicle.apply_control(control)  # <-- NEW

            if latest_image:
                image_array = carla_image_to_pygame(latest_image)
                surface = pygame.surfarray.make_surface(image_array.swapaxes(0, 1))
                display.blit(surface, (0, 0))

            pygame.display.flip()
            clock.tick(30)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        pygame.quit()
        if camera is not None:
            camera.destroy()
        if vehicle is not None:
            vehicle.destroy()
        if bus is not None:
            bus.destroy()
        for traffic_car in traffic_cars:
            traffic_car.destroy()

if __name__ == "__main__":
    main()
