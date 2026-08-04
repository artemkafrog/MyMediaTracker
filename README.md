
<div align="center">

# MediaTracker

> Smart media collection manager with modern web interface, video playback, and analytics.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-2.7-4FC08D.svg)](https://vuejs.org/)

</div>

---

## Description

**MediaTracker** is a full-featured application for managing your personal media collection. Whether you have movies, TV shows, or video courses — keep everything organized, track your progress, and get insights from your library.


## Interface Gallery

<div align="center">

<!-- ===== SCREENSHOTS ===== -->
<table border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 820px; margin: 0 auto;">

<tr>
<td style="padding: 10px 0; text-align: center;">

<!-- Collection Grid -->
<img src="screenshots/collection_grid.png" alt="Collection Grid" width="100%" style="max-width: 800px; display: block; margin: 0 auto;">
<br>
<strong>Collection</strong>
<br>
<em>View all your media in a clean grid or list layout</em>

</td>
</tr>

<tr>
<td style="padding: 10px 0; text-align: center;">

<!-- Charts -->
<img src="screenshots/charts.png" alt="Analytics Dashboard" width="100%" style="max-width: 800px; display: block; margin: 0 auto;">
<br>
<strong>Charts</strong>
<br>
<em>Visualize your collection with interactive charts</em>

</td>
</tr>

<tr>
<td style="padding: 10px 0; text-align: center;">

<!-- Reports -->
<img src="screenshots/reports.png" alt="Analytics Dashboard" width="100%" style="max-width: 800px; display: block; margin: 0 auto;">
<br>
<strong>Reports</strong>
<br>
<em>Generate your collection reports</em>

</td>
</tr>

<tr>
<td style="padding: 10px 0; text-align: center;">

<!-- Analytics -->
<img src="screenshots/analytics.png" alt="Analytics Dashboard" width="100%" style="max-width: 800px; display: block; margin: 0 auto;">
<br>
<strong>Analytics Dashboard</strong>
<br>
<em>Visualize your collection with interactive charts and statistics</em>

</td>
</tr>

<tr>
<td style="padding: 10px 0; text-align: center;">

<!-- Player -->
<img src="screenshots/player.png" alt="Video Player" width="100%" style="max-width: 800px; display: block; margin: 0 auto;">
<br>
<strong>Video Player</strong>
<br>
<em>Built-in player with progress tracking and fullscreen</em>

</td>
</tr>

</table>

</div>

---

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip 
- (optional) ffmpeg for thumbnail generation

### Installation

```bash
# Clone the repository
git clone https://github.com/artemkafrog/MyMediaTracker.git
cd MyMediaTracker

# Create and activate virtual environment 
python -m venv venv
source venv/bin/activate  
# On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the server
python run.py
```

The application will automatically open in your browser at `http://localhost:5000`

### First Launch

1. Click **Add** or **Batch Add** to upload your first videos
2. Fill in metadata (title, genres, rating, etc.)
3. Start watching and tracking your collection!

---


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  Made with ❤️ by <a href="https://github.com/artemkafrog">artemkafrog</a>
</div>
