import json

def test():
    venue_map = {
        "Green Yoga Friedrichshain 3": {"Name": "Green Yoga Friedrichshain 3", "Rating": "4.8"},
        "bruto": {"Name": "bruto", "Rating": "4.9"}
    }
    
    classes = [
        {"Venue": "Green Yoga Friedrichshain, Gärtnerstraße 3, 10245 Berlin"},
        {"Venue": "Bruto, Oranienstraße 183"}
    ]
    
    for c_info in classes:
        print(f"Testing {c_info['Venue']}")
        matched_venue = None
        class_venue_base = c_info["Venue"].split(',')[0].strip()
        
        # Check for an exact substring match first
        for v_name, v_data in venue_map.items():
            if class_venue_base.lower() in v_name.lower() or v_name.lower() in class_venue_base.lower():
                matched_venue = v_data
                break
                
        # If exact substring doesn't work, try difflib for closest string match
        if not matched_venue:
            import difflib
            all_venue_names = list(venue_map.keys())
            matches = difflib.get_close_matches(class_venue_base, all_venue_names, n=1, cutoff=0.4)
            if matches:
                matched_venue = venue_map[matches[0]]
                
        if matched_venue:
            print(f"Matched: {matched_venue['Name']}")
        else:
            print("Failed to match")

test()
