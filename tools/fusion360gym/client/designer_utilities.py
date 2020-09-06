# return the sketch that has the largest area
def largest_area(sketches):
    max_area = 0
    return_sketch = None
    for sketch in sketches:
        areas = []
        if "profiles" in sketch:
            profiles = sketch["profiles"]
            for profile in profiles:
                areas.append(profiles[profile]["properties"]["area"])
            sum_area = sum(areas)
            average_area = sum_area / len(areas)
            if sum_area > max_area:
                max_area = sum_area
                return_sketch = sketch
    return return_sketch, return_sketch["name"], average_area, max_area


# return the centroid of a sketch
def calculate_sketch_centroid(sketch):
    profiles = sketch["profiles"]
    # calcuate the centroid of the sketch
    sketch_centroid = {"x": 0, "y": 0, "z": 0}
    for profile in profiles:
        sketch_centroid["x"] += profiles[profile]["properties"]["centroid"]["x"]
        sketch_centroid["y"] += profiles[profile]["properties"]["centroid"]["y"]
        sketch_centroid["z"] += profiles[profile]["properties"]["centroid"]["z"]
    for key in sketch_centroid:
        sketch_centroid[key] /= len(profiles)
    return sketch_centroid   


# calculate average area from profiles 
def calculate_average_area(profiles):
    average_area = 0
    for profile_id in profiles:
        average_area += profiles[profile_id]["properties"]["area"]
    return average_area / len(profiles)


# traverse all the sketches
def traverse_sketches(json_data):
    sketches = []
    timeline = json_data["timeline"]
    entities = json_data["entities"]
    for timeline_object in timeline:
        entity_uuid = timeline_object["entity"]
        entity_index = timeline_object["index"]
        entity = entities[entity_uuid]
        # we only want sketches with profiles 
        if entity["type"] == "Sketch" and "profiles" in entity:
            sketches.append(entity)
    return sketches



