"""
Example: Using SiteSage with Google Maps for US Locations

This example demonstrates how to use SiteSage to evaluate
a coffee shop location in New York City using Google Maps APIs.
"""

import os
from tools.map import MapTool

# Configure for Google Maps
os.environ["GOOGLE_MAPS_API_KEY"] = "your_google_maps_api_key_here"
os.environ["OPENAI_API_KEY"] = "your_openai_key_here"

def main():
    # Initialize MapTool with Google Maps
    print("Initializing SiteSage with Google Maps...")
    map_tool = MapTool(map_choice="google_maps")
    
    # Example 1: Get place information
    print("\n=== Example 1: Get Place Info ===")
    address = "Times Square, New York, NY"
    place = map_tool.getPlaceInfo(address)
    
    print(f"Place: {place['name']}")
    print(f"Address: {place['address']}")
    print(f"Coordinates: ({place['lat']}, {place['lng']})")
    print(f"Category: {place['category']}")
    
    # Example 2: Find nearby coffee shops
    print("\n=== Example 2: Find Nearby Coffee Shops ===")
    nearby_coffee = map_tool.getNearbyPlaces(
        origin=place,
        descriptive_types=["cafe", "coffee shop"],
        radius=500,  # 500 meters
        num_pages=1
    )
    
    print(f"Found {len(nearby_coffee)} nearby coffee shops:")
    for i, shop in enumerate(nearby_coffee[:5], 1):
        print(f"  {i}. {shop['name']}")
        print(f"     Address: {shop['address']}")
        print(f"     Rating: {shop.get('rating', 'N/A')}")
        print(f"     Reviews: {shop.get('review_count', 'N/A')}")
    
    # Example 3: Find nearby transit stations
    print("\n=== Example 3: Find Nearby Transit ===")
    nearby_transit = map_tool.getNearbyPlaces(
        origin=place,
        descriptive_types=["subway station", "bus station"],
        radius=300,
        num_pages=1
    )
    
    print(f"Found {len(nearby_transit)} nearby transit stations:")
    for i, station in enumerate(nearby_transit[:3], 1):
        print(f"  {i}. {station['name']}")
    
    # Example 4: Calculate distances
    print("\n=== Example 4: Calculate Walking Distances ===")
    if nearby_coffee:
        destinations = nearby_coffee[:3]
        distances = map_tool.getDistances(
            origin=place,
            destinations=destinations,
            mode="walk"
        )
        
        for dist in distances:
            name = dist['destination'].get('name', 'Unknown')
            distance_m = dist['distance_m']
            duration_s = dist['duration_s']
            print(f"  To {name}:")
            print(f"    Distance: {distance_m:.0f}m ({distance_m * 0.000621371:.2f} miles)")
            print(f"    Walk time: {duration_s / 60:.1f} minutes")
    
    # Example 5: Generate map visualization
    print("\n=== Example 5: Generate Static Map ===")
    viz = map_tool.getMapVisualization(
        origin=place,
        zoom=15,
        overlays=nearby_coffee[:5] if nearby_coffee else []
    )
    
    print(f"Map URL: {viz['url'][:100]}...")
    print(f"Number of markers: {len(viz['overlays']) + 1}")  # +1 for origin

def example_site_analysis():
    """
    Example of a complete site analysis for a coffee shop
    """
    print("\n\n=== COMPLETE SITE ANALYSIS EXAMPLE ===\n")
    
    map_tool = MapTool(map_choice="google_maps")
    
    # Target location
    target_address = "5th Avenue and 42nd Street, New York, NY"
    print(f"Analyzing location: {target_address}")
    
    target_place = map_tool.getPlaceInfo(target_address)
    print(f"✓ Geocoded to: ({target_place['lat']:.6f}, {target_place['lng']:.6f})")
    
    # Analyze competition
    print("\n1. Competition Analysis")
    competitors = map_tool.getNearbyPlaces(
        origin=target_place,
        descriptive_types=["cafe", "coffee shop", "bakery"],
        radius=300,
        num_pages=2
    )
    print(f"   Found {len(competitors)} competing establishments within 300m")
    avg_rating = sum(c.get('rating', 0) for c in competitors) / len(competitors) if competitors else 0
    print(f"   Average competitor rating: {avg_rating:.2f}")
    
    # Analyze foot traffic generators
    print("\n2. Foot Traffic Analysis")
    traffic_generators = map_tool.getNearbyPlaces(
        origin=target_place,
        descriptive_types=["subway station", "bus station", "tourist attraction", "office building"],
        radius=500,
        num_pages=1
    )
    print(f"   Found {len(traffic_generators)} traffic generators within 500m")
    for tg in traffic_generators[:5]:
        print(f"   - {tg['name']} ({tg['category']})")
    
    # Analyze amenities
    print("\n3. Nearby Amenities")
    amenities = map_tool.getNearbyPlaces(
        origin=target_place,
        descriptive_types=["parking", "park", "shopping mall"],
        radius=400,
        num_pages=1
    )
    print(f"   Found {len(amenities)} amenities within 400m")
    
    # Summary
    print("\n=== ANALYSIS SUMMARY ===")
    print(f"Location: {target_place['name']}")
    print(f"Competition Level: {'High' if len(competitors) > 10 else 'Moderate' if len(competitors) > 5 else 'Low'}")
    print(f"Foot Traffic Potential: {'High' if len(traffic_generators) > 5 else 'Moderate' if len(traffic_generators) > 2 else 'Low'}")
    print(f"Amenity Score: {len(amenities)}/10")

if __name__ == "__main__":
    # Check API key is set
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        print("ERROR: GOOGLE_MAPS_API_KEY not set!")
        print("Please set your Google Maps API key:")
        print("  export GOOGLE_MAPS_API_KEY='your_key_here'  # Linux/Mac")
        print("  $env:GOOGLE_MAPS_API_KEY='your_key_here'    # Windows PowerShell")
        exit(1)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        exit(1)
    
    # Run examples
    main()
    
    # Uncomment to run complete site analysis
    # example_site_analysis()
