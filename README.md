# E-Paper Image Frame

A web-based digital photo frame application designed for e-ink displays, featuring intelligent image cropping, slideshow functionality, and an intuitive web interface for managing your photo collection.

## 🖼️ Features

### Core Functionality
- **E-Ink Display Support**: Optimized for e-paper displays with proper image rendering
- **Web Interface**: Modern, responsive web UI for managing images remotely
- **Smart Cropping**: Visual crop editor with aspect ratio locking to display dimensions
- **Slideshow Mode**: Automatic image rotation with configurable timing
- **Multi-Image Upload**: Bulk upload support for efficient photo management

### Image Management
- **Drag & Drop Crop Tool**: Intuitive visual cropping with real-time preview
- **Metadata Editing**: Add titles and descriptions to your images
- **Image Controls**: Enable/disable, display instantly, or delete images
- **Usage Tracking**: See how many times each image has been displayed
- **Thumbnail Generation**: Automatic thumbnail creation for fast browsing

### Advanced Features
- **Developer Mode**: Test without physical e-ink display
- **Crop-Fill Rendering**: Eliminates letterboxing by intelligently cropping to fit
- **Cache Busting**: Automatic image refresh for immediate visual feedback
- **Mobile Responsive**: Works seamlessly on phones, tablets, and desktops

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Optional: Inky e-paper display (compatible models)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ryanlane/epaper-image-frame.git
   cd epaper-image-frame
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   python migrate_db.py
   ```

4. **Start the application**
   ```bash
   python app.py
   ```

5. **Access the web interface**
   Open your browser to `http://localhost:8080`

## 📁 Project Structure

```
epaper-image-frame/
├── app.py                 # Main FastAPI application
├── database.py           # Database configuration and setup
├── models.py             # SQLAlchemy database models
├── migrate_db.py         # Database migration script
├── requirements.txt      # Python dependencies
├── photo_frame.db        # SQLite database (created automatically)
├── static/
│   ├── css/             # Stylesheets
│   ├── uploads/         # Full-size uploaded images
│   ├── thumbs/          # Generated thumbnails
│   └── current.jpg      # Currently displayed image
├── templates/           # Jinja2 HTML templates
│   └── partials/        # Reusable template components
└── utils/
    ├── eframe_inky.py   # E-ink display interface
    └── image_utils.py   # Image processing utilities
```

## 🖥️ Usage Guide

### Adding Images
1. Click **"Upload Images"** in the navigation
2. Select multiple images or drag & drop
3. Images are automatically processed and thumbnails generated

### Editing Images
1. Click the **✏️ Edit** button on any image card
2. Modify title and description as needed
3. Click **"Crop Settings ▼"** to expand the crop editor
4. Drag the orange rectangle to select the crop area
5. Resize using the corner handles (aspect ratio locked to display)
6. Click **"Save"** to apply changes

### Managing Display
- **▶️ Play Now**: Immediately display the image on the e-ink screen
- **🖼️/🚫 Toggle**: Enable/disable images in slideshow rotation
- **🗑️ Delete**: Remove image from collection

### Settings Configuration
- **Resolution**: Set your e-ink display dimensions (e.g., "800,480")
- **Image Root**: Directory for full-size images
- **Thumb Root**: Directory for thumbnails
- **Slideshow**: Configure automatic image rotation timing

## 🔧 Technical Details

### Technology Stack
- **Backend**: FastAPI (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Image Processing**: Pillow (PIL) for resizing and cropping
- **Templates**: Jinja2 templating engine

### Database Schema
- **Images**: Stores image metadata, crop settings, and usage statistics
- **Settings**: Stores application configuration and display parameters

### Image Processing Pipeline
1. **Upload**: Multi-file upload with validation
2. **Processing**: Automatic thumbnail generation
3. **Storage**: Organized file system with unique filenames
4. **Rendering**: Crop-aware rendering to match display aspect ratio
5. **Display**: E-ink optimized output

## 🎨 Crop System

The advanced cropping system ensures your images always look perfect on your e-ink display:

- **Aspect Ratio Locking**: Crop selections automatically maintain your display's aspect ratio
- **Visual Editor**: Drag and resize the crop area with real-time preview
- **Percentage-Based**: Crop coordinates stored as percentages for resolution independence
- **Smart Defaults**: New images default to full-frame (0%, 0%, 100%, 100%)

## 🔄 Slideshow Features

- **Automatic Rotation**: Configure timing for hands-free operation
- **Smart Selection**: Only enabled images participate in slideshow
- **Manual Override**: "Play Now" button for immediate display
- **Usage Tracking**: Monitor which images are displayed most frequently

## 🐛 Development Mode

For development and testing without physical e-ink hardware:

- Automatic detection when Inky library is unavailable
- Console logging instead of display output
- Full web interface functionality preserved
- Banner notification of developer mode status

## 📱 Mobile Support

The responsive design works seamlessly across devices:

- **Mobile**: Touch-friendly interface with collapsible navigation
- **Tablet**: Optimized layout for medium screens
- **Desktop**: Full-featured experience with keyboard shortcuts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for e-ink displays, particularly Inky series
- Inspired by the need for elegant, low-power digital photo frames
- Community contributions welcome!