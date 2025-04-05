import pygame
import cv2
import requests
import os
import json
from pygame.locals import *

# --- Config ---
API_KEY = "2b10KtRB4bBaEG9ZGC0NoklkzO"
PROJECT = "all"
api_endpoint = f"https://my-api.plantnet.org/v2/identify/{PROJECT}?api-key={API_KEY}"

# --- Init ---
pygame.init()
width, height = 360, 600  # Phone-sized dimensions
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("FloralQuest")

# Load background image
background_image = pygame.image.load("assets/background.png")  # Add your background image path here
background_image = pygame.transform.scale(background_image, (width, height))

clock = pygame.time.Clock()

font_path = "assets/Font_2.ttf"
# Font sizes
title_font_large = pygame.font.Font(font_path, 80)
title_font_medium = pygame.font.Font(font_path, 60)
header_font = pygame.font.Font(font_path, 30)
plant_name_font = pygame.font.Font(font_path, 20)
button_font = pygame.font.Font(font_path, 25)
points_font = pygame.font.Font(font_path, 20)
small_font = pygame.font.Font(font_path, 16)

# --- States ---
STATE_TITLE = "title"
STATE_CAMERA = "camera"
STATE_RESULT = "result"
STATE_INDEX = "index"
STATE_SHOP = "shop"
state = STATE_TITLE
result_text = ""
result_description = ""
found_flowers = {}  # Dictionary to store plant names and count of occurrences

# --- Plant Index ---
PLANT_INDEX_DIR = "plant_index"
PLANT_INDEX_FILE = os.path.join(PLANT_INDEX_DIR, "index.json")
SAVE_FILE = "game_data.json"

# Create directories if they don't exist
if not os.path.exists(PLANT_INDEX_DIR):
    os.makedirs(PLANT_INDEX_DIR)

# Load game data
total_points = 0
owned_seeds = {}
shop_scroll_y = 0
scroll_speed = 20 

def load_game_data():
    global total_points, owned_seeds
    try:
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
            total_points = data.get('total_points', 0)
            owned_seeds = data.get('owned_seeds', {})
    except (FileNotFoundError, json.JSONDecodeError):
        total_points = 0
        owned_seeds = {}
        save_game_data()

def save_game_data():
    data = {
        'total_points': total_points,
        'owned_seeds': owned_seeds
    }
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f)

load_game_data()

# Load existing plant index
plant_index = {}
if os.path.exists(PLANT_INDEX_FILE):
    with open(PLANT_INDEX_FILE, 'r') as f:
        plant_index = json.load(f)

# --- Shop Items ---
shop_items = [
    {"name": "Sunflower Seed", "price": 100, "image": "assets/sunflower_seed.jpg"},
    {"name": "Rose Seed", "price": 150, "image": "assets/rose_seed.jpg"},
    {"name": "Tulip Seed", "price": 120, "image": "assets/tulip_seed.jpg"},
    {"name": "Lavender Seed", "price": 180, "image": "assets/lavender_seed.jpeg"},
    {"name": "Daisy Seed", "price": 90, "image": "assets/daisy_seed.jpeg"},
    {"name": "Orchid Seed", "price": 250, "image": "assets/orchid_seed.jpg"},
    {"name": "Mystery Seed", "price": 500, "image": "assets/question_seed.png"}
]

# --- Colors ---
WHITE = (255, 255, 255)
LIGHT_BLUE = (173, 216, 230)
DARK_GREEN = (0, 128, 0)
BLACK = (0, 0, 0)
GREEN = (65, 196, 93)
LIGHT_GREEN = (144, 238, 144)
INDEX_BG = (240, 255, 240)
SHOP_BG = (255, 250, 240)
BUTTON_HOVER = (100, 200, 100)

# --- Buttons ---
def draw_button(text, rect, color, text_color, font_size=25, hover_color=BUTTON_HOVER):
    mouse_pos = pygame.mouse.get_pos()
    btn_color = hover_color if rect.collidepoint(mouse_pos) else color
    pygame.draw.rect(screen, btn_color, rect, border_radius=10)
    font = pygame.font.Font(font_path, font_size)
    label = font.render(text, True, text_color)
    label_rect = label.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2))
    screen.blit(label, label_rect)
    return rect.collidepoint(mouse_pos)

# Button definitions
start_button = pygame.Rect(80, 480, 200, 50)
index_button = pygame.Rect(80, 410, 200, 50)
shop_button = pygame.Rect(80, 340, 200, 50)
capture_button = pygame.Rect(130, 530, 100, 40)
restart_button = pygame.Rect(80, 450, 200, 50)
home_button = pygame.Rect(80, 520, 200, 50)
back_button = pygame.Rect(10, 10, 80, 30)
shop_back_button = pygame.Rect(10, 10, 80, 30)
buy_button = pygame.Rect(width//2 - 50, height - 60, 100, 40)

# --- Webcam ---
cap = None

# --- Functions ---
def identify_plant(image_path):
    image_data = open(image_path, 'rb')
    data = {'organs': ['flower']}
    files = [('images', (image_path, image_data))]

    req = requests.Request('POST', url=api_endpoint, files=files, data=data)
    prepared = req.prepare()
    s = requests.Session()
    response = s.send(prepared)
    json_result = response.json()

    if 'results' in json_result and json_result['results']:
        best_match = json_result['results'][0]
        species = best_match['species']
        sci_name = species['scientificName']
        common_names = species.get('commonNames', [])
        common = common_names[0] if common_names else "Unknown"
        description = get_wikipedia_description(sci_name)
        return f"{common} ({sci_name})", description
    else:
        return "No match found.", ""

def get_wikipedia_description(scientific_name):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{scientific_name.replace(' ', '_')}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('extract', 'No description available.')
    else:
        return "No description available."

def update_points(plant_name):
    global total_points
    if plant_name == "No match found.":
        return
    elif plant_name not in found_flowers:
        found_flowers[plant_name] = 1
        total_points += 100
    elif found_flowers[plant_name] == 1:
        found_flowers[plant_name] += 1
        total_points += 10
    save_game_data()

def save_to_plant_index(plant_name, image_path):
    if plant_name == "No match found.":
        return
    
    base_name = plant_name.split("(")[0].strip().replace(" ", "_").lower()
    counter = 1
    while True:
        image_filename = f"{base_name}_{counter}.jpg"
        full_path = os.path.join(PLANT_INDEX_DIR, image_filename)
        if not os.path.exists(full_path):
            break
        counter += 1
    
    os.rename(image_path, full_path)
    
    if plant_name not in plant_index:
        plant_index[plant_name] = {
            "scientific_name": plant_name.split("(")[-1].rstrip(")"),
            "common_name": plant_name.split("(")[0].strip(),
            "images": [image_filename],
            "count": 1
        }
    else:
        plant_index[plant_name]["images"].append(image_filename)
        plant_index[plant_name]["count"] += 1
    
    with open(PLANT_INDEX_FILE, 'w') as f:
        json.dump(plant_index, f, indent=2)

def draw_flower_index():
    pygame.draw.rect(screen, INDEX_BG, (0, 0, width, height))
    
    title = header_font.render("Plant Index", True, DARK_GREEN)
    screen.blit(title, (width//2 - title.get_width()//2, 20))
    
    points_text = points_font.render(f"Total Points: {total_points}", True, DARK_GREEN)
    screen.blit(points_text, (width//2 - points_text.get_width()//2, 60))
    
    draw_button("Back", back_button, LIGHT_BLUE, BLACK, 18)
    
    scroll_area = pygame.Rect(10, 100, width-20, height-120)
    pygame.draw.rect(screen, WHITE, scroll_area, border_radius=10)
    
    content_height = len(plant_index) * 100
    content_surface = pygame.Surface((scroll_area.width-20, max(scroll_area.height, content_height)))
    content_surface.fill(WHITE)
    
    y_offset = 10
    for plant_name, data in plant_index.items():
        entry_rect = pygame.Rect(10, y_offset, scroll_area.width-40, 80)
        pygame.draw.rect(content_surface, LIGHT_GREEN, entry_rect, border_radius=8)
        
        common_name = data["common_name"]
        if len(common_name) > 15:
            common_name = common_name[:15] + "..."
        name_text = plant_name_font.render(f"{common_name} (x{data['count']})", True, BLACK)
        content_surface.blit(name_text, (15, y_offset + 10))
        
        sci_name = data["scientific_name"]
        if len(sci_name) > 20:
            sci_name = sci_name[:20] + "..."
        sci_text = small_font.render(sci_name, True, BLACK)
        content_surface.blit(sci_text, (15, y_offset + 35))
        
        if data["images"]:
            try:
                img_path = os.path.join(PLANT_INDEX_DIR, data["images"][0])
                img = pygame.image.load(img_path)
                img = pygame.transform.scale(img, (60, 60))
                content_surface.blit(img, (entry_rect.width - 70, y_offset + 10))
            except:
                pass
        
        y_offset += 90
    
    screen.blit(content_surface, (scroll_area.x+10, scroll_area.y+10), 
                (0, 0, scroll_area.width-20, scroll_area.height))

def draw_shop():
    global total_points, shop_scroll_y
    
    pygame.draw.rect(screen, SHOP_BG, (0, 0, width, height))
    
    title = header_font.render("Seed Shop", True, DARK_GREEN)
    screen.blit(title, (width//2 - title.get_width()//2, 20))
    
    points_text = points_font.render(f"Your Points: {total_points}", True, DARK_GREEN)
    screen.blit(points_text, (width//2 - points_text.get_width()//2, 60))
    
    draw_button("Back", shop_back_button, LIGHT_BLUE, BLACK, 18)
    
    # Shop items area
    scroll_area = pygame.Rect(10, 100, width-20, height-160)
    pygame.draw.rect(screen, WHITE, scroll_area, border_radius=10)
    
    # Calculate content height needed
    content_height = len(shop_items) * 110
    max_scroll = max(0, content_height - scroll_area.height)
    shop_scroll_y = max(0, min(shop_scroll_y, max_scroll))
    
    # Create content surface
    content_surface = pygame.Surface((scroll_area.width-20, content_height))
    content_surface.fill(WHITE)
    
    # Draw all items on the content surface
    for i, item in enumerate(shop_items):
        y_offset = 10 + i * 110
        
        entry_rect = pygame.Rect(10, y_offset, scroll_area.width-40, 100)
        
        # Highlight if hovered
        mouse_pos = pygame.mouse.get_pos()
        adjusted_mouse_y = mouse_pos[1] - scroll_area.y - 10 + shop_scroll_y
        is_hovered = (10 <= mouse_pos[0] <= scroll_area.width-10 and 
                     y_offset <= adjusted_mouse_y <= y_offset + 100)
        
        entry_color = (200, 255, 200) if is_hovered else LIGHT_GREEN
        pygame.draw.rect(content_surface, entry_color, entry_rect, border_radius=8)
        
        # Item name
        name_text = plant_name_font.render(item["name"], True, BLACK)
        content_surface.blit(name_text, (15, y_offset + 10))
        
        # Price
        price_text = small_font.render(f"{item['price']} points", True, BLACK)
        content_surface.blit(price_text, (15, y_offset + 40))
        
        # Owned count
        owned = owned_seeds.get(item["name"], 0)
        owned_text = small_font.render(f"Owned: {owned}", True, BLACK)
        content_surface.blit(owned_text, (15, y_offset + 65))
        
        # Item image
        try:
            img = pygame.image.load(item["image"])
            img = pygame.transform.scale(img, (60, 60))
            content_surface.blit(img, (entry_rect.width - 70, y_offset + 20))
        except:
            pass
    
    # Draw visible portion of content
    screen.blit(content_surface, (scroll_area.x+10, scroll_area.y+10), 
                (0, shop_scroll_y, scroll_area.width-20, scroll_area.height))
    
    # Draw scroll bar if needed
    if content_height > scroll_area.height:
        scroll_ratio = scroll_area.height / content_height
        scroll_bar_height = scroll_area.height * scroll_ratio
        scroll_bar_y = scroll_area.y + 10 + (shop_scroll_y / content_height) * (scroll_area.height - 20)
        
        pygame.draw.rect(screen, (200, 200, 200), 
                         (scroll_area.right - 8, scroll_area.y + 10, 6, scroll_area.height - 20))
        pygame.draw.rect(screen, (150, 150, 150), 
                         (scroll_area.right - 8, scroll_bar_y, 6, scroll_bar_height), border_radius=3)
    
# --- Main Loop ---
running = True
while running:
    screen.fill(WHITE)
    screen.blit(background_image, (0, 0))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
        elif event.type == pygame.MOUSEWHEEL:
            if state == STATE_SHOP:
                shop_scroll_y -= event.y * scroll_speed
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                if state == STATE_TITLE:
                    if start_button.collidepoint(event.pos):
                        cap = cv2.VideoCapture(0)
                        state = STATE_CAMERA
                    elif index_button.collidepoint(event.pos):
                        state = STATE_INDEX
                    elif shop_button.collidepoint(event.pos):
                        state = STATE_SHOP
                
                elif state == STATE_SHOP:
                    if shop_back_button.collidepoint(event.pos):
                        state = STATE_TITLE
                    else:
                        # Handle shop item clicks
                        mouse_pos = event.pos
                        if (10 <= mouse_pos[0] <= width-10 and 
                            100 <= mouse_pos[1] <= height-60):
                            
                        # Calculate which item was clicked
                            item_index = (mouse_pos[1] - 100 + shop_scroll_y) // 110
                            if 0 <= item_index < len(shop_items):
                                item = shop_items[item_index]
                            if total_points >= item["price"]:
                                total_points -= item["price"]
                                owned_seeds[item["name"]] = owned_seeds.get(item["name"], 0) + 1
                                save_game_data()
            if state == STATE_TITLE:
                if start_button.collidepoint(event.pos):
                    cap = cv2.VideoCapture(0)
                    state = STATE_CAMERA
                elif index_button.collidepoint(event.pos):
                    state = STATE_INDEX
                elif shop_button.collidepoint(event.pos):
                    state = STATE_SHOP
                    
            elif state == STATE_INDEX and back_button.collidepoint(event.pos):
                state = STATE_TITLE
            elif state == STATE_SHOP and shop_back_button.collidepoint(event.pos):
                state = STATE_TITLE
            elif state == STATE_RESULT and home_button.collidepoint(event.pos):
                state = STATE_TITLE
            elif state == STATE_CAMERA and capture_button.collidepoint(event.pos):
                ret, frame = cap.read()
                if ret:
                    image_path = "captured.jpg"
                    cv2.imwrite(image_path, frame)
                    cap.release()
                    cap = None
                    result_text, result_description = identify_plant(image_path)
                    update_points(result_text)
                    save_to_plant_index(result_text, image_path)
                    state = STATE_RESULT

            elif state == STATE_RESULT and restart_button.collidepoint(event.pos):
                cap = cv2.VideoCapture(0)
                state = STATE_CAMERA
                result_text = ""
                result_description = ""

    # --- State Renders ---
    if state == STATE_TITLE:
        # Title with "Floral" larger than "Quest"
        floral_text = title_font_large.render("Floral", True, DARK_GREEN)
        quest_text = title_font_medium.render("Quest", True, DARK_GREEN)
        
        screen.blit(floral_text, (width//2 - floral_text.get_width()//2, 100))
        screen.blit(quest_text, (width//2 - quest_text.get_width()//2, 180))
        
        draw_button("Start Webcam", start_button, LIGHT_BLUE, BLACK)
        draw_button("Plant Index", index_button, LIGHT_BLUE, BLACK)
        draw_button("Seed Shop", shop_button, LIGHT_BLUE, BLACK)
        
    elif state == STATE_INDEX:
        draw_flower_index()
        
    elif state == STATE_SHOP:
        draw_shop()
        
    elif state == STATE_CAMERA:
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (width, height-100))
            frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            screen.blit(frame_surface, (0, 0))
        
        # Camera controls overlay
        overlay = pygame.Surface((width, 100), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))  # Semi-transparent black
        screen.blit(overlay, (0, height-100))
        
        # Camera frame
        pygame.draw.rect(screen, WHITE, (width//2 - 110, height-90, 220, 80), 2, border_radius=5)
        
        draw_button("Capture", capture_button, GREEN, WHITE, 20)

    elif state == STATE_RESULT:
        pygame.draw.rect(screen, INDEX_BG, (0, 0, width, height))
        
        title = header_font.render("Identification Result", True, DARK_GREEN)
        screen.blit(title, (width//2 - title.get_width()//2, 30))
        
        points_text = points_font.render(f"Points: {total_points}", True, DARK_GREEN)
        screen.blit(points_text, (width//2 - points_text.get_width()//2, 80))
        
        wrapped_result = result_text
        if len(result_text) > 30:
            parts = []
            current = ""
            for word in result_text.split():
                if len(current) + len(word) + 1 <= 30:
                    current += " " + word if current else word
                else:
                    parts.append(current)
                    current = word
            if current:
                parts.append(current)
            wrapped_result = "\n".join(parts)
        
        y_pos = 130
        for line in wrapped_result.split("\n"):
            name_text = plant_name_font.render(line, True, BLACK)
            screen.blit(name_text, (width//2 - name_text.get_width()//2, y_pos))
            y_pos += 30
        
        draw_button("Identify Another", restart_button, LIGHT_BLUE, BLACK)
        draw_button("Return Home", home_button, LIGHT_BLUE, BLACK)
    
    pygame.display.flip()
    clock.tick(30)

if cap:
    cap.release()
pygame.quit()
