import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import json
import os
import math

# --- Configuration & Scaling ---
# Base sizes (will be scaled)
BASE_NODE_WIDTH = 180 # Increased base size
BASE_NODE_HEIGHT = 100 # Increased base size
BASE_FONT_SIZE = 10    # Base font size for node text, will be scaled
BASE_ARROW_SIZE = 12   # Base arrow size for connections

# Global zoom level
INITIAL_ZOOM_LEVEL = 1.0 # Start with no zoom, or e.g., 1.5 for 4K if desired
MIN_ZOOM = 0.2
MAX_ZOOM = 3.0

# Colors
NODE_COLOR = "lightblue"
NODE_SELECTED_COLOR = "deepskyblue"
TEXT_COLOR = "black"
LINE_COLOR = "gray"
ARROW_COLOR = "black"
CANVAS_BG_COLOR = "white"

class ConversationEditorApp:
    def __init__(self, master):
        self.master = master
        master.title("Conversation Editor")
        master.geometry("1400x900") # Slightly larger default window

        self.conversation_data = {}
        self.file_path = None
        self.zoom_level = INITIAL_ZOOM_LEVEL

        # --- Style Configuration for larger UI elements ---
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam', 'alt', 'default', 'classic' - clam often looks good

        # Increase default font size for all widgets
        default_font = ("Arial", int(10 * self.zoom_level) if self.zoom_level >=1 else 10) # Scale font for high DPI
        self.style.configure(".", font=default_font, padding=int(5 * self.zoom_level) if self.zoom_level >=1 else 5) # General padding
        self.style.configure("TButton", font=("Arial", int(11*self.zoom_level) if self.zoom_level >=1 else 11), padding=int(6 * self.zoom_level) if self.zoom_level >=1 else 6)
        self.style.configure("TLabel", font=("Arial", int(10*self.zoom_level) if self.zoom_level >=1 else 10))
        self.style.configure("TEntry", font=("Arial", int(10*self.zoom_level) if self.zoom_level >=1 else 10), padding=int(4 * self.zoom_level) if self.zoom_level >=1 else 4)
        self.style.configure("Danger.TButton", foreground="white", background="darkred", font=("Arial", int(11*self.zoom_level) if self.zoom_level >=1 else 11))
        self.style.map("Danger.TButton", background=[('active', 'red')])


        # --- UI Panes ---
        self.main_pane = tk.PanedWindow(master, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=8)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self.canvas_frame = ttk.Frame(self.main_pane) # Removed fixed width/height
        self.main_pane.add(self.canvas_frame, stretch="always")

        self.properties_frame_container = ttk.Frame(self.main_pane, width=int(450 * self.zoom_level) if self.zoom_level >=1 else 450) # Scaled properties panel width
        self.main_pane.add(self.properties_frame_container, stretch="never")

        # Canvas
        self.canvas = tk.Canvas(self.canvas_frame, bg=CANVAS_BG_COLOR, scrollregion=(0,0,4000,3000)) # Larger initial scroll
        
        self.hbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.vbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Properties Panel
        self.properties_panel = ttk.Frame(self.properties_frame_container, padding="10")
        self.properties_panel.pack(fill=tk.BOTH, expand=True)
        
        self.current_selected_node_id = None
        self.node_visuals = {}
        self.selected_canvas_item_id = None
        self._drag_data = {"item": None, "x": 0, "y": 0}

        # Menu
        menubar = tk.Menu(master)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Load JSON", command=self.load_json)
        filemenu.add_command(label="Save JSON", command=self.save_json)
        filemenu.add_command(label="Save JSON As...", command=self.save_json_as)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=master.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Add Node", command=self.add_new_node_prompt)
        menubar.add_cascade(label="Edit", menu=editmenu)

        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label="Zoom In (+)", command=lambda: self.zoom(1.2))
        viewmenu.add_command(label="Zoom Out (-)", command=lambda: self.zoom(0.8))
        viewmenu.add_command(label="Reset Zoom (100%)", command=lambda: self.zoom_reset())
        menubar.add_cascade(label="View", menu=viewmenu)
        master.config(menu=menubar)
        master.bind_all("<Control-s>", self.handle_save_shortcut)

        # Canvas Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        # Mouse wheel zoom (cross-platform)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel) # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)   # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)   # Linux scroll down


        self.build_properties_panel(None)
        
    def handle_save_shortcut(self, event=None):
        """Handles the Ctrl+S shortcut. The event argument is passed by Tkinter."""
        print("Ctrl+S pressed!") # For debugging
        self.save_json()
        return "break"

    # --- Scaling Helper Properties ---
    @property
    def node_width(self):
        return BASE_NODE_WIDTH * self.zoom_level
    @property
    def node_height(self):
        return BASE_NODE_HEIGHT * self.zoom_level
    @property
    def node_font_size(self):
        return int(BASE_FONT_SIZE * self.zoom_level)
    @property
    def arrow_size(self):
        s = int(BASE_ARROW_SIZE * self.zoom_level)
        return (s, int(s*1.2), int(s*0.5)) # arrowshape tuple

    # --- Zoom Functions ---
    def zoom(self, factor, event=None):
        new_zoom = self.zoom_level * factor
        if MIN_ZOOM <= new_zoom <= MAX_ZOOM:
            
            # Get canvas coordinates of the mouse pointer if event is provided
            if event:
                mouse_x_canvas = self.canvas.canvasx(event.x)
                mouse_y_canvas = self.canvas.canvasy(event.y)
            else: # Zoom to center of current view if no event (e.g. menu click)
                mouse_x_canvas = self.canvas.canvasx(self.canvas.winfo_width() / 2)
                mouse_y_canvas = self.canvas.canvasy(self.canvas.winfo_height() / 2)

            self.zoom_level = new_zoom
            
            # Redraw everything with new zoom
            self.draw_all_nodes_and_connections() # This will use new scaled sizes

            # Adjust scroll region and view to keep the mouse pointer's world coordinate in the same screen position
            # New canvas coordinates for the same world point
            new_mouse_x_canvas = mouse_x_canvas * factor 
            new_mouse_y_canvas = mouse_y_canvas * factor

            # How much the view needs to shift
            delta_x_view = new_mouse_x_canvas - self.canvas.canvasx(event.x if event else self.canvas.winfo_width() / 2)
            delta_y_view = new_mouse_y_canvas - self.canvas.canvasy(event.y if event else self.canvas.winfo_height() / 2)
            
            self.canvas.xview_scroll(int(delta_x_view / (self.canvas.winfo_width() * self.canvas.xview()[1] - self.canvas.xview()[0])), "units") # Approximate
            self.canvas.yview_scroll(int(delta_y_view / (self.canvas.winfo_height() * self.canvas.yview()[1] - self.canvas.yview()[0])), "units") # Approximate


    def zoom_reset(self):
        # Calculate the center of the current view in world coordinates
        view_center_x_canvas = self.canvas.canvasx(self.canvas.winfo_width() / 2)
        view_center_y_canvas = self.canvas.canvasy(self.canvas.winfo_height() / 2)
        world_center_x = view_center_x_canvas / self.zoom_level
        world_center_y = view_center_y_canvas / self.zoom_level

        self.zoom_level = INITIAL_ZOOM_LEVEL
        self.draw_all_nodes_and_connections()
        
        # Try to re-center the view on the same world point
        new_view_center_x_canvas = world_center_x * self.zoom_level
        new_view_center_y_canvas = world_center_y * self.zoom_level

        self.canvas.xview_moveto( (new_view_center_x_canvas - self.canvas.winfo_width()/2) / (self.canvas.bbox("all")[2] or 1) )
        self.canvas.yview_moveto( (new_view_center_y_canvas - self.canvas.winfo_height()/2) / (self.canvas.bbox("all")[3] or 1) )


    def on_mouse_wheel(self, event):
        factor = 0
        # Respond to Linux wheel events
        if event.num == 4:
            factor = 1.1  # Zoom in
        elif event.num == 5:
            factor = 0.9  # Zoom out
        # Respond to Windows wheel events
        elif event.delta > 0:
            factor = 1.1
        elif event.delta < 0:
            factor = 0.9
        
        if factor:
            self.zoom(factor, event) # Pass event for zoom to mouse position
            return "break" # Prevents default scroll

    # --- World to Canvas Coordinates (and vice-versa for mouse events) ---
    # For drawing, we use world coordinates * zoom_level
    # For mouse events, we get canvas coordinates / zoom_level to get world coordinates

    def world_to_canvas_coords(self, world_x, world_y):
        # For drawing, coordinates are already considered "world" space,
        # but visual sizes are scaled. This might be confusing.
        # Let's assume self.node_visuals stores WORLD coordinates.
        return world_x * self.zoom_level, world_y * self.zoom_level

    def canvas_to_world_coords(self, canvas_x_on_screen, canvas_y_on_screen):
        # Convert screen click to canvas scrollable coordinate, then to world
        true_canvas_x = self.canvas.canvasx(canvas_x_on_screen)
        true_canvas_y = self.canvas.canvasy(canvas_y_on_screen)
        return true_canvas_x / self.zoom_level, true_canvas_y / self.zoom_level


    def draw_node(self, node_id, world_x, world_y): # x, y are world coordinates
        node_data = self.conversation_data.get(node_id, {})
        
        # Calculate scaled dimensions for drawing
        draw_x = world_x * self.zoom_level
        draw_y = world_y * self.zoom_level
        w = self.node_width
        h = self.node_height
        font = ("Arial", self.node_font_size)

        rect_id = self.canvas.create_rectangle(
            draw_x, draw_y, draw_x + w, draw_y + h,
            fill=NODE_COLOR, outline="black", width=max(1, int(2 * self.zoom_level)), tags=("node", node_id)
        )
        text_id = self.canvas.create_text(
            draw_x + w / 2, draw_y + h / 2,
            text=node_id, fill=TEXT_COLOR, font=font, tags=("node_text", node_id), width=w - (10 * self.zoom_level)
        )
        # Store WORLD coordinates along with canvas item IDs
        self.node_visuals[node_id] = {'rect': rect_id, 'text': text_id, 
                                      'world_x': world_x, 'world_y': world_y, 
                                      'editor_pos': (world_x, world_y)} # editor_pos IS world_x, world_y
        return rect_id

    def draw_all_nodes_and_connections(self):
        self.canvas.delete("all")
        self.node_visuals.clear()
        
        # Initial placement values (world coordinates)
        world_x_place, world_y_place = 50, 50
        col_count = 0
        # Max cols based on current canvas view width and scaled node width
        # This logic for initial placement can be improved
        canvas_view_width = self.canvas.winfo_width() / self.zoom_level # Effective world width in view
        max_cols = math.floor((canvas_view_width - 100) / (BASE_NODE_WIDTH + 50)) if canvas_view_width > 100 else 3
        max_cols = max(1, max_cols) # ensure at least 1 column

        sorted_node_ids = sorted(self.conversation_data.keys())

        for node_id in sorted_node_ids:
            node_data = self.conversation_data[node_id]
            # Use stored position if available, otherwise calculate
            if 'editor_pos' in node_data and isinstance(node_data['editor_pos'], (list, tuple)) and len(node_data['editor_pos']) == 2:
                nx, ny = node_data['editor_pos'] # These are world coordinates
            else: # Calculate initial world position
                nx, ny = world_x_place, world_y_place
                # ... (calculation logic) ...
                if node_id in self.conversation_data: # Store calculated world position
                    self.conversation_data[node_id]['editor_pos'] = (nx, ny)
            
            self.draw_node(node_id, nx, ny) # Pass world coordinates

        self.draw_connections()
        
        # Update scrollregion after drawing all scaled items
        all_bbox = self.canvas.bbox("all")
        if all_bbox:
            self.canvas.config(scrollregion=all_bbox)
        else:
            self.canvas.config(scrollregion=(0,0,1,1)) # Avoid error if canvas is empty

    def draw_connections(self):
        self.canvas.delete("connection")
        for source_id, node_data in self.conversation_data.items():
            if source_id not in self.node_visuals: continue

            source_vis = self.node_visuals[source_id]
            # Center of the node in DRAWING coordinates for lines
            sx_draw = (source_vis['world_x'] * self.zoom_level) + self.node_width / 2
            sy_draw = (source_vis['world_y'] * self.zoom_level) + self.node_height / 2
            
            targets_drawn = set()
            
            node_targets = []
            if "choices" in node_data:
                for choice in node_data["choices"]:
                    if choice.get("next_node_id"): node_targets.append(choice["next_node_id"])
            if "entry_mode" in node_data:
                if "secrets" in node_data["entry_mode"]:
                    for secret in node_data["entry_mode"]["secrets"]:
                        if secret.get("next_node_id"): node_targets.append(secret["next_node_id"])
                if node_data["entry_mode"].get("default_next_node_id"):
                     node_targets.append(node_data["entry_mode"]["default_next_node_id"])

            for target_id in node_targets:
                if target_id and target_id in self.node_visuals and target_id not in targets_drawn:
                    self.draw_line_with_arrow(sx_draw, sy_draw, target_id)
                    targets_drawn.add(target_id)
    
    def draw_line_with_arrow(self, sx_draw, sy_draw, target_id): # sx_draw, sy_draw are DRAWING coords
        target_vis = self.node_visuals[target_id]
        # Target center in DRAWING coordinates
        tx_draw = (target_vis['world_x'] * self.zoom_level) + self.node_width / 2
        ty_draw = (target_vis['world_y'] * self.zoom_level) + self.node_height / 2

        angle = math.atan2(ty_draw - sy_draw, tx_draw - sx_draw)
        
        # Intersection with target node's border (using scaled node dimensions)
        end_x_draw = tx_draw - (self.node_width / 2) * math.cos(angle)
        end_y_draw = ty_draw - (self.node_height / 2) * math.sin(angle)
        
        # Adjust start point (scaled offset)
        offset = 10 * self.zoom_level
        start_x_draw = sx_draw + (offset * math.cos(angle))
        start_y_draw = sy_draw + (offset * math.sin(angle))

        self.canvas.create_line(start_x_draw, start_y_draw, end_x_draw, end_y_draw, 
                                fill=LINE_COLOR, width=max(1, int(1.5 * self.zoom_level)), 
                                arrow=tk.LAST, arrowshape=self.arrow_size, tags="connection")

    def on_canvas_press(self, event):
        # event.x, event.y are SCREEN coordinates relative to the canvas widget
        
        # Convert screen click to true canvas coordinates (accounting for scrolling)
        true_canvas_x = self.canvas.canvasx(event.x)
        true_canvas_y = self.canvas.canvasy(event.y)

        # Convert true canvas coordinates to WORLD coordinates (accounting for zoom)
        world_x_click = true_canvas_x / self.zoom_level
        world_y_click = true_canvas_y / self.zoom_level
        
        # Debugging:
        # print(f"Screen click: ({event.x}, {event.y})")
        # print(f"True Canvas click: ({true_canvas_x}, {true_canvas_y})")
        # print(f"World click: ({world_x_click:.2f}, {world_y_click:.2f})")

        clicked_node_id = None
        clicked_canvas_rect_id = None

        # Iterate through your drawn nodes to check for a hit in WORLD coordinates
        # Sort by z-order (drawing order) might be better if nodes could overlap significantly,
        # but for now, iterating should be okay if they are mostly distinct.
        for node_id, vis_info in self.node_visuals.items():
            # Node bounds in WORLD coordinates (using BASE sizes as world dimensions)
            n_world_x1 = vis_info['world_x']
            n_world_y1 = vis_info['world_y']
            n_world_x2 = vis_info['world_x'] + BASE_NODE_WIDTH  # Use BASE_NODE_WIDTH for world dimensions
            n_world_y2 = vis_info['world_y'] + BASE_NODE_HEIGHT # Use BASE_NODE_HEIGHT for world dimensions

            # Debugging each node's bounds:
            # print(f"Checking node {node_id}: World Bounds ({n_world_x1:.2f}, {n_world_y1:.2f}) to ({n_world_x2:.2f}, {n_world_y2:.2f})")

            if n_world_x1 <= world_x_click <= n_world_x2 and \
               n_world_y1 <= world_y_click <= n_world_y2:
                clicked_node_id = node_id
                clicked_canvas_rect_id = vis_info['rect'] # The Tkinter canvas ID for the rectangle
                # print(f"HIT on node {node_id}!")
                break # Found a node, stop checking
        
        if clicked_node_id:
            self.select_node(clicked_node_id, clicked_canvas_rect_id)
            self._drag_data["item"] = self.node_visuals[clicked_node_id]['rect'] # Tkinter ID of rect
            self._drag_data["text_item"] = self.node_visuals[clicked_node_id]['text'] # Tkinter ID of text
            self._drag_data["node_id"] = clicked_node_id
            # Store initial drag position in WORLD coordinates (where the click happened)
            self._drag_data["world_x_start_click"] = world_x_click
            self._drag_data["world_y_start_click"] = world_y_click
            # Store the node's original WORLD position when drag starts
            self._drag_data["node_original_world_x"] = self.node_visuals[clicked_node_id]['world_x']
            self._drag_data["node_original_world_y"] = self.node_visuals[clicked_node_id]['world_y']
        else:
            self.deselect_node()
            self._drag_data["item"] = None


    def on_canvas_drag(self, event):
        if self._drag_data["item"] and self._drag_data["node_id"]:
            # Current mouse position in WORLD coordinates
            current_world_x_click = self.canvas.canvasx(event.x) / self.zoom_level
            current_world_y_click = self.canvas.canvasy(event.y) / self.zoom_level
            
            # Delta of mouse movement in WORLD coordinates since drag started
            delta_world_x = current_world_x_click - self._drag_data["world_x_start_click"]
            delta_world_y = current_world_y_click - self._drag_data["world_y_start_click"]

            # New WORLD position for the node's top-left
            new_node_world_x = self._drag_data["node_original_world_x"] + delta_world_x
            new_node_world_y = self._drag_data["node_original_world_y"] + delta_world_y
            
            node_id_dragged = self._drag_data["node_id"]
            vis = self.node_visuals[node_id_dragged]

            # Calculate how much the DRAWING coordinates need to move from their CURRENT position
            # Current drawing top-left of the rectangle
            # (The actual current position of canvas items is what matters for 'move')
            # We can get this from canvas.coords or calculate based on last known world + zoom
            
            # Let's recalculate the delta for canvas item movement based on the new world position
            # compared to the old world position of the items.
            
            old_item_draw_x = vis['world_x'] * self.zoom_level 
            old_item_draw_y = vis['world_y'] * self.zoom_level
            
            new_item_draw_x = new_node_world_x * self.zoom_level
            new_item_draw_y = new_node_world_y * self.zoom_level
            
            # This is the delta in drawing coordinates to apply to the items
            move_canvas_x = new_item_draw_x - old_item_draw_x
            move_canvas_y = new_item_draw_y - old_item_draw_y

            # Move the Tkinter canvas items by this delta in DRAWING coordinates
            self.canvas.move(self._drag_data["item"], move_canvas_x, move_canvas_y)       # Move rectangle
            self.canvas.move(self._drag_data["text_item"], move_canvas_x, move_canvas_y) # Move text

            # Update stored WORLD position in our visual dictionary
            vis['world_x'] = new_node_world_x
            vis['world_y'] = new_node_world_y
            vis['editor_pos'] = (new_node_world_x, new_node_world_y)
            
            self.draw_connections()
            
    def on_canvas_release(self, event):
        if self._drag_data["item"] and self._drag_data["node_id"]:
            node_id_dragged = self._drag_data["node_id"]
            if node_id_dragged in self.conversation_data:
                self.conversation_data[node_id_dragged]['editor_pos'] = self.node_visuals[node_id_dragged]['editor_pos']
            self.canvas.config(scrollregion=self.canvas.bbox("all")) # Update scroll at end of drag
        
        self._drag_data["item"] = None # Reset drag data

    # --- select_node, deselect_node, build_properties_panel etc. ---
    # These need to be aware that node_visuals stores world_x, world_y
    # and that drawing functions use these world_x, world_y scaled by zoom_level.
    # Highlighting and other direct canvas operations should use the stored canvas item IDs.
    def select_node(self, node_id, canvas_item_id_rect):
        self.deselect_node()
        self.current_selected_node_id = node_id
        self.selected_canvas_item_id = canvas_item_id_rect # This is the rectangle's Tkinter ID
        self.canvas.itemconfig(self.selected_canvas_item_id, fill=NODE_SELECTED_COLOR, outline="black", width=max(2, int(3 * self.zoom_level)))
        self.build_properties_panel(node_id)

    def deselect_node(self):
        if self.selected_canvas_item_id: # Check if it's a valid canvas item ID
            try: # It might have been deleted
                self.canvas.itemconfig(self.selected_canvas_item_id, fill=NODE_COLOR, outline="black", width=max(1, int(2 * self.zoom_level)))
            except tk.TclError:
                pass # Item might no longer exist
        self.current_selected_node_id = None
        self.selected_canvas_item_id = None
        self.clear_properties_panel()
        self.build_properties_panel(None) # Show empty panel

    # ... (Rest of the methods: clear_properties_panel, build_properties_panel,
    # create_property_editor, create_choice_editor, create_secret_editor,
    # update_node_property, add_new_node_prompt, delete_node,
    # convert_node_to_type, add_choice, add_secret, remove_choice_or_secret
    # should largely remain the same, as they operate on the data model
    # or create Tkinter widgets for the properties panel, which are already scaled by ttk.Style)

    # --- Minor adjustments might be needed in property panel creation if font sizes there feel too small/large ---
    # For example, in create_property_editor, for tk.Text:
    # text_widget = tk.Text(frame, height=3, width=30, wrap=tk.WORD, font=default_font)
    # And for ttk.Entry, they should pick up the styled font.

    # ... [The following methods are copied from your previous version, ensure they are present] ...
    def load_json(self): # Ensure this is fully defined
        path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.conversation_data = json.load(f)
                self.file_path = path
                self.master.title(f"Conversation Editor - {os.path.basename(path)}")
                self.zoom_level = INITIAL_ZOOM_LEVEL # Reset zoom on new file load
                self.draw_all_nodes_and_connections()
                self.deselect_node() # Clear properties panel and selection
            except Exception as e:
                messagebox.showerror("Error Loading JSON", f"Could not load file: {e}")

    def save_json_data(self, path): # Ensure this is fully defined
        if not path:
            messagebox.showerror("Save Error", "No file path specified.")
            return
        try:
            for node_id, visual_info in self.node_visuals.items():
                if node_id in self.conversation_data and 'editor_pos' in visual_info: # editor_pos IS world_x, world_y
                    self.conversation_data[node_id]['editor_pos'] = visual_info['editor_pos']

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_data, f, indent=2, ensure_ascii=False)
            self.file_path = path
            self.master.title(f"Conversation Editor - {os.path.basename(path)}")
            messagebox.showinfo("Save Successful", f"Conversation saved to {path}")
        except Exception as e:
            messagebox.showerror("Error Saving JSON", f"Could not save file: {e}")
    
    def save_json(self): # Ensure this is fully defined
        if self.file_path:
            self.save_json_data(self.file_path)
        else:
            self.save_json_as()

    def save_json_as(self): # Ensure this is fully defined
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="conversation.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.save_json_data(path)
    
    def clear_properties_panel(self): # Ensure this is fully defined
        for widget in self.properties_panel.winfo_children():
            widget.destroy()

    def build_properties_panel(self, node_id): # Ensure this is fully defined and uses scaled fonts if needed
        self.clear_properties_panel()
        scaled_header_font = ("Arial", int(14 * (self.zoom_level if self.zoom_level > 1 else 1.2)), "bold") # Ensure header is visible
        
        if not node_id or node_id not in self.conversation_data:
            ttk.Label(self.properties_panel, text="No node selected or node data missing.").pack(pady=10)
            return

        node_data = self.conversation_data[node_id]
        ttk.Label(self.properties_panel, text=f"Editing Node: {node_id}", font=scaled_header_font).pack(pady=5)
        
        id_frame = ttk.Frame(self.properties_panel)
        id_frame.pack(fill=tk.X, pady=2)
        ttk.Label(id_frame, text="Node ID:").pack(side=tk.LEFT, padx=5)
        id_var = tk.StringVar(value=node_id)
        # Simple Node ID changer (can be complex due to references)
        def _change_node_id():
            old_id = node_id
            new_id_val = simpledialog.askstring("Change Node ID", f"Enter new ID for '{old_id}':", initialvalue=old_id, parent=self.master)
            if new_id_val and new_id_val != old_id:
                if new_id_val in self.conversation_data:
                    messagebox.showerror("Error", f"Node ID '{new_id_val}' already exists.")
                    return
                # Update data
                self.conversation_data[new_id_val] = self.conversation_data.pop(old_id)
                # Update visuals dictionary key
                self.node_visuals[new_id_val] = self.node_visuals.pop(old_id)
                # Update canvas tags (this is the tricky part for direct canvas item retagging)
                # Easiest is to redraw, or manually retag one by one if performance is an issue.
                # For now, let's re-tag the specific items:
                self.canvas.itemconfig(self.node_visuals[new_id_val]['rect'], tags=("node", new_id_val))
                self.canvas.itemconfig(self.node_visuals[new_id_val]['text'], text=new_id_val, tags=("node_text", new_id_val))
                
                # Update references in other nodes (CRITICAL for complex changes)
                for nid_ref, ndata_ref in self.conversation_data.items():
                    if "choices" in ndata_ref:
                        for choice in ndata_ref["choices"]:
                            if choice.get("next_node_id") == old_id: choice["next_node_id"] = new_id_val
                    if "entry_mode" in ndata_ref:
                        if ndata_ref["entry_mode"].get("default_next_node_id") == old_id:
                            ndata_ref["entry_mode"]["default_next_node_id"] = new_id_val
                        if "secrets" in ndata_ref["entry_mode"]:
                            for secret in ndata_ref["entry_mode"]["secrets"]:
                                if secret.get("next_node_id") == old_id: secret["next_node_id"] = new_id_val
                
                self.current_selected_node_id = new_id_val # Update selection
                self.draw_all_nodes_and_connections() # Redraw to reflect new ID on canvas and connections
                self.build_properties_panel(new_id_val) # Rebuild panel with new ID

        id_entry = ttk.Entry(id_frame, textvariable=id_var, state='readonly')
        id_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(id_frame, text="Change ID", command=_change_node_id).pack(side=tk.LEFT, padx=2)


        self.create_property_editor(self.properties_panel, node_id, "sprite_text", "Sprite Text:", multiline=True)
        self.create_property_editor(self.properties_panel, node_id, "sprite_image", "Sprite Image URL:")
        self.create_property_editor(self.properties_panel, node_id, "editor_pos", "Editor Position (x,y):", readonly=True)

        if "choices" in node_data:
            choices_frame = ttk.LabelFrame(self.properties_panel, text="Choices", padding="5")
            choices_frame.pack(fill=tk.X, pady=5, padx=5, expand=True)
            for i, choice in enumerate(node_data["choices"]):
                self.create_choice_editor(choices_frame, node_id, i, choice)
            ttk.Button(choices_frame, text="Add Choice", command=lambda: self.add_choice(node_id)).pack(pady=5)
        
        if "entry_mode" in node_data:
            entry_frame = ttk.LabelFrame(self.properties_panel, text="Entry Mode", padding="5")
            entry_frame.pack(fill=tk.X, pady=5, padx=5, expand=True)
            self.create_property_editor(entry_frame, node_id, "entry_mode.prompt_text", "Prompt Text:")
            self.create_property_editor(entry_frame, node_id, "entry_mode.default_next_node_id", "Default Next Node:")
            
            secrets_frame = ttk.LabelFrame(entry_frame, text="Secrets", padding="3")
            secrets_frame.pack(fill=tk.X, pady=3, padx=3, expand=True)
            if "secrets" in node_data["entry_mode"]:
                for i, secret in enumerate(node_data["entry_mode"]["secrets"]):
                    self.create_secret_editor(secrets_frame, node_id, i, secret)
            ttk.Button(secrets_frame, text="Add Secret", command=lambda: self.add_secret(node_id)).pack(pady=3)
        
        if "choices" not in node_data and "entry_mode" not in node_data:
            interaction_buttons_frame = ttk.Frame(self.properties_panel)
            interaction_buttons_frame.pack(pady=10)
            ttk.Button(interaction_buttons_frame, text="Make 'Choices' Node", command=lambda: self.convert_node_to_type(node_id, "choices")).pack(side=tk.LEFT, padx=5)
            ttk.Button(interaction_buttons_frame, text="Make 'Entry Mode' Node", command=lambda: self.convert_node_to_type(node_id, "entry_mode")).pack(side=tk.LEFT, padx=5)

        ttk.Button(self.properties_panel, text="Delete This Node", style="Danger.TButton", command=lambda: self.delete_node(node_id)).pack(pady=20)


    def create_property_editor(self, parent, node_id, key_path, label_text, multiline=False, readonly=False): # Ensure this is fully defined
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label_text).pack(side=tk.LEFT, padx=5, anchor="nw") # anchor to north-west

        def get_value(data_dict, path_str):
            keys = path_str.split('.')
            val = data_dict
            try:
                for key in keys:
                    if isinstance(val, list) and key.isdigit(): # Handle list indices like choices.0.text
                        val = val[int(key)]
                    else:
                        val = val[key]
                return val if val is not None else ""
            except (KeyError, TypeError, IndexError): return ""
        
        current_val = get_value(self.conversation_data[node_id], key_path)
        
        if multiline:
            text_widget = tk.Text(frame, height=4, width=30, wrap=tk.WORD, font=("Arial", int(10*self.zoom_level) if self.zoom_level >=1 else 10)) # Scaled font
            text_widget.insert(tk.END, current_val)
            if readonly: text_widget.config(state=tk.DISABLED)
            else: text_widget.bind("<FocusOut>", lambda event, p=parent, n=node_id, k=key_path, w=text_widget: self.update_node_property(p, n, k, w.get("1.0", tk.END).strip()))
            text_widget.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        else:
            var = tk.StringVar(value=current_val)
            entry = ttk.Entry(frame, textvariable=var, font=("Arial", int(10*self.zoom_level) if self.zoom_level >=1 else 10)) # Scaled font
            if readonly: entry.config(state=tk.DISABLED)
            else: entry.bind("<FocusOut>", lambda event, p=parent, n=node_id, k=key_path, v=var: self.update_node_property(p, n, k, v.get()))
            entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def create_choice_editor(self, parent, node_id, choice_index, choice_data): # Ensure this is fully defined
        choice_frame = ttk.Frame(parent, relief=tk.GROOVE, borderwidth=1, padding="3")
        choice_frame.pack(fill=tk.X, pady=(5,2), padx=3, expand=True) # expand
        ttk.Label(choice_frame, text=f"Choice {choice_index + 1}").pack(anchor="w", pady=(0,3))
        
        self.create_property_editor(choice_frame, node_id, f"choices.{choice_index}.text", "Text:")
        self.create_property_editor(choice_frame, node_id, f"choices.{choice_index}.next_node_id", "Next Node ID:")
        self.create_property_editor(choice_frame, node_id, f"choices.{choice_index}.item", "Item (opt):")
        self.create_property_editor(choice_frame, node_id, f"choices.{choice_index}.action", "Action (opt):")
        ttk.Button(choice_frame, text="Remove Choice", style="Danger.TButton", command=lambda: self.remove_choice_or_secret(node_id, "choices", choice_index)).pack(pady=(5,2), anchor="e")

    def create_secret_editor(self, parent, node_id, secret_index, secret_data): # Ensure this is fully defined
        secret_frame = ttk.Frame(parent, relief=tk.GROOVE, borderwidth=1, padding="3")
        secret_frame.pack(fill=tk.X, pady=(5,2), padx=3, expand=True) # expand
        ttk.Label(secret_frame, text=f"Secret {secret_index + 1}").pack(anchor="w", pady=(0,3))
        
        self.create_property_editor(secret_frame, node_id, f"entry_mode.secrets.{secret_index}.input", "Input Text:")
        self.create_property_editor(secret_frame, node_id, f"entry_mode.secrets.{secret_index}.next_node_id", "Next Node ID:")
        ttk.Button(secret_frame, text="Remove Secret", style="Danger.TButton", command=lambda: self.remove_choice_or_secret(node_id, "entry_mode.secrets", secret_index)).pack(pady=(5,2), anchor="e")

    def update_node_property(self, parent_widget_context, node_id, key_path, value): # Ensure this is fully defined
        # Path like "choices.0.text" or "entry_mode.secrets.1.input" or "sprite_text"
        keys = key_path.split('.')
        data_ptr = self.conversation_data[node_id]
        
        for i, key_segment in enumerate(keys[:-1]):
            if key_segment.isdigit(): # Array index for choices or secrets
                idx = int(key_segment)
                # Ensure list exists and is long enough
                # This part needs to be careful not to create unwanted structures if path is wrong
                if not isinstance(data_ptr, list) or idx >= len(data_ptr) :
                    # This indicates an issue or a need to create the list/item
                    # For simplicity, assume lists (choices/secrets) are created by "Add" buttons
                    print(f"Warning: Path segment '{key_segment}' for index {idx} in '{key_path}' implies list, but context is: {type(data_ptr)}")
                    # Potentially try to fix it if next key is not an index.
                    # If the path implies a list (e.g. choices.0) but 'choices' isn't a list, we have a problem.
                    # This function assumes the structure mostly exists, especially lists.
                    if not isinstance(data_ptr, dict) or key_segment not in data_ptr: # Create if missing and next is dict key
                         if i + 1 < len(keys) and not keys[i+1].isdigit():
                            data_ptr[key_segment] = {}
                         else: # If next is digit, this is likely a wrong path for an array.
                            print(f"Error: Trying to access/create index in non-list or missing list for {key_path}")
                            return # Avoid further errors
                    
                if isinstance(data_ptr, dict) and key_segment in data_ptr:
                    data_ptr = data_ptr[key_segment]
                elif isinstance(data_ptr, list) and idx < len(data_ptr):
                    data_ptr = data_ptr[idx]
                else:
                    # Error or create structure. Let's log error and return to avoid breaking.
                    print(f"Error: Cannot navigate path '{key_path}' at segment '{key_segment}'")
                    return

            else: # Object key
                if key_segment not in data_ptr or not isinstance(data_ptr[key_segment], (dict, list)):
                     # If next segment is an index, create a list, else a dict
                    if i + 1 < len(keys) and keys[i+1].isdigit():
                        data_ptr[key_segment] = []
                    else:
                        data_ptr[key_segment] = {}
                data_ptr = data_ptr[key_segment]
        
        final_key = keys[-1]
        is_list_final_key = final_key.isdigit()
        if is_list_final_key: final_key = int(final_key)

        optional_keys_for_deletion = ["sprite_image", "item", "action", "default_next_node_id", "prompt_text"]
        is_optional_key = any(key_path.endswith(op_key) for op_key in optional_keys_for_deletion)

        if value == "" and is_optional_key:
            if isinstance(data_ptr, dict) and final_key in data_ptr:
                del data_ptr[final_key]
            elif isinstance(data_ptr, list) and isinstance(final_key, int) and final_key < len(data_ptr) :
                # This would imply trying to "delete" a list item by emptying one of its string properties.
                # Usually, we remove list items via a "Remove" button, not by emptying a field.
                # So, if it's an optional string field within a list item, set it to empty.
                 data_ptr[final_key] = value # Or del data_ptr[final_key] if that specific property should be removed
        else:
            if isinstance(data_ptr, list) and isinstance(final_key, int):
                if final_key < len(data_ptr): data_ptr[final_key] = value
                # else: print("Error: list index out of bounds for", key_path) # Should be handled by Add buttons
            elif isinstance(data_ptr, dict):
                data_ptr[final_key] = value
            else:
                print(f"Error: Cannot set property. data_ptr is not dict or list for final_key of {key_path}")


        if "next_node_id" in key_path: # If a link changed
            self.draw_connections()
        
        # Instead of rebuilding the whole panel which can be slow and lose focus,
        # we could be more targeted. But for now, full rebuild is simpler.
        self.build_properties_panel(self.current_selected_node_id)

    def add_new_node_prompt(self): # Ensure this is fully defined
        new_id = simpledialog.askstring("New Node", "Enter ID for the new node:", parent=self.master)
        if new_id:
            if new_id in self.conversation_data:
                messagebox.showerror("Error", f"Node ID '{new_id}' already exists.")
                return
            
            # Simplified new node position
            world_cx, world_cy = self.canvas_to_world_coords(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)
            
            self.conversation_data[new_id] = {
                "sprite_text": f"Text for {new_id}", "sprite_image": "",
                "editor_pos": (world_cx, world_cy) 
            }
            # Draw the node using its world coordinates
            self.draw_node(new_id, world_cx, world_cy) 
            self.select_node(new_id, self.node_visuals[new_id]['rect'])
            self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def delete_node(self, node_id): # Ensure this is fully defined
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete node '{node_id}'?"):
            if node_id in self.conversation_data: del self.conversation_data[node_id]
            if node_id in self.node_visuals:
                self.canvas.delete(self.node_visuals[node_id]['rect'])
                self.canvas.delete(self.node_visuals[node_id]['text'])
                del self.node_visuals[node_id]
            
            for nid, ndata in self.conversation_data.items():
                if "choices" in ndata:
                    for choice in ndata["choices"]:
                        if choice.get("next_node_id") == node_id: choice["next_node_id"] = ""
                if "entry_mode" in ndata:
                    if ndata["entry_mode"].get("default_next_node_id") == node_id:
                         ndata["entry_mode"]["default_next_node_id"] = ""
                    if "secrets" in ndata["entry_mode"]:
                        for secret in ndata["entry_mode"]["secrets"]:
                            if secret.get("next_node_id") == node_id: secret["next_node_id"] = ""
            self.draw_all_nodes_and_connections()
            self.deselect_node()

    def convert_node_to_type(self, node_id, type_str): # Ensure this is fully defined
        if node_id not in self.conversation_data: return
        if type_str == "choices":
            self.conversation_data[node_id].pop("entry_mode", None)
            self.conversation_data[node_id]["choices"] = [{"text": "New Choice", "next_node_id": ""}]
        elif type_str == "entry_mode":
            self.conversation_data[node_id].pop("choices", None)
            self.conversation_data[node_id]["entry_mode"] = {
                "prompt_text": "Enter...", "secrets": [{"input": "secret", "next_node_id": ""}], "default_next_node_id": ""
            }
        self.build_properties_panel(node_id)
        self.draw_connections()

    def add_choice(self, node_id): # Ensure this is fully defined
        if node_id not in self.conversation_data or "choices" not in self.conversation_data[node_id]:
            self.convert_node_to_type(node_id, "choices") 
            return 
        self.conversation_data[node_id]["choices"].append({"text": "New Choice", "next_node_id": ""})
        self.build_properties_panel(node_id)

    def add_secret(self, node_id): # Ensure this is fully defined
        if node_id not in self.conversation_data or "entry_mode" not in self.conversation_data[node_id]:
            self.convert_node_to_type(node_id, "entry_mode")
            return
        if "secrets" not in self.conversation_data[node_id]["entry_mode"]:
            self.conversation_data[node_id]["entry_mode"]["secrets"] = []
        self.conversation_data[node_id]["entry_mode"]["secrets"].append({"input": "new_secret", "next_node_id": ""})
        self.build_properties_panel(node_id)

    def remove_choice_or_secret(self, node_id, list_key_str, item_index): # Ensure this is fully defined
        data_ptr = self.conversation_data[node_id]
        keys = list_key_str.split('.')
        
        for key_segment in keys[:-1]: data_ptr = data_ptr[key_segment]
        
        target_list = data_ptr[keys[-1]]
        if 0 <= item_index < len(target_list): del target_list[item_index]
        if not target_list: del data_ptr[keys[-1]]
        self.build_properties_panel(node_id)
        self.draw_connections()


if __name__ == '__main__':
    root = tk.Tk()
    # DPI Awareness (Windows specific, but good to have)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1) # Try for per-monitor DPI awareness
    except ImportError: # Not windows
        pass
    except AttributeError: # Older Windows
        try:
            windll.user32.SetProcessDPIAware()
        except: pass


    app = ConversationEditorApp(root)
    if os.path.exists("conversation.json"):
        app.file_path = os.path.abspath("conversation.json") # Use absolute path
        try:
            with open(app.file_path, 'r', encoding='utf-8') as f:
                app.conversation_data = json.load(f)
            root.title(f"Conversation Editor - {os.path.basename(app.file_path)}")
            app.draw_all_nodes_and_connections() # Initial draw
        except Exception as e:
            messagebox.showwarning("Auto-load failed", f"Could not auto-load conversation.json: {e}")

    root.mainloop()