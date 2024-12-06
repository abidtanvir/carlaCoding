import carla
import pygame
import numpy as np
import time

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

def spawn_traffic_cars(world, blueprint_library, num_cars=5):
    """Spawn traffic cars around the main car."""
    traffic_cars = []
    spawn_points = world.get_map().get_spawn_points()
    for i in range(num_cars):
        # Random spawn point, but you can make this fixed as well
        spawn_point = spawn_points[i % len(spawn_points)]
        vehicle_bp = blueprint_library.find('vehicle.tesla.model3')
        vehicle = world.try_spawn_actor(vehicle_bp, spawn_point)
        if vehicle:
            traffic_cars.append(vehicle)
            # Make the vehicle move
            vehicle.set_autopilot(True)  # Vehicles will drive automatically
            print(f"Spawned traffic car at {spawn_point.location}")
        else:
            print("Failed to spawn traffic car.")
    
    return traffic_cars

def main():
    pygame.init()
    display = pygame.display.set_mode((display_width, display_height), pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.display.set_caption("CARLA Simulation")
    clock = pygame.time.Clock()

    traffic_cars = []  # Initialize traffic_cars to avoid reference errors

    try:
        # Connect to CARLA server
        client = carla.Client(CARLA_SERVER_HOST, CARLA_SERVER_PORT)
        client.set_timeout(10.0)
        
        # Load a specific town
        town_name = "Town03"
        print(f"Loading town: {town_name}")
        client.load_world(town_name)
        world = client.get_world()
        
        # Give time for the world to load
        time.sleep(2)

        # Get the blueprint library and list all available vehicles
        blueprint_library = world.get_blueprint_library()
        print("Available vehicle blueprints:")
        for blueprint in blueprint_library.filter('vehicle.*'):
            print(blueprint.id)
        
        # Use a specific vehicle blueprint for the static vehicle
        vehicle_bp = blueprint_library.find('vehicle.tesla.model3')

        # Use a predefined spawn point for the static vehicle
        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            print("No spawn points available!")
            return
        
        spawn_point = spawn_points[0]  # Static vehicle at the first spawn point
        print(f"Using spawn point: {spawn_point.location}")

        # Try to spawn the vehicle
        vehicle = world.try_spawn_actor(vehicle_bp, spawn_point)
        if vehicle is None:
            print("Vehicle spawn failed!")
            return
        print(f"Vehicle spawned at {spawn_point.location}")
        
        # Attach a camera for third-person view
        camera_bp = blueprint_library.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', str(display_width))
        camera_bp.set_attribute('image_size_y', str(display_height))
        camera_bp.set_attribute('fov', '110')

        camera_transform = carla.Transform(carla.Location(x=-6.0, y=0, z=3.0), carla.Rotation(pitch=-15))
        camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)
        
        latest_image = None

        def process_image(image):
            nonlocal latest_image
            latest_image = image

        camera.listen(lambda image: process_image(image))

        # Spawn additional traffic cars
        traffic_cars = spawn_traffic_cars(world, blueprint_library, num_cars=10)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

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
        if 'camera' in locals() and camera is not None:
            camera.destroy()
        if 'vehicle' in locals() and vehicle is not None:
            vehicle.destroy()
        for traffic_car in traffic_cars:
            traffic_car.destroy()  # Cleanup traffic cars

if __name__ == "__main__":
    main()
