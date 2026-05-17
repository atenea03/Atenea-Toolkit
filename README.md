<div align="center">

# 🖼️ Atenea Toolkit

**The ultimate localized suite to convert, optimize, resize, and compress images and game server textures.**
No internet connection required. Just open, select your module, and process.

![Version](https://img.shields.io/badge/version-v2026-F5A800?style=flat-square&labelColor=1a1a1a)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square&labelColor=1a1a1a)
![License](https://img.shields.io/badge/license-Atenea_Store_Tools-F5A800?style=flat-square&labelColor=1a1a1a)

</div>

---

## 📦 Folder Contents

| File / Folder | Description |
|------|-------------|
| `atenea_toolkit.exe` | ✅ **The program.** Double-click to open. |
| `texconv.exe` | ⚙️ Microsoft DirectX Texture Converter (Essential for the DDS Studio). |
| `atenea_toolkit.py` | Source code (developers only). |
| `atenea_toolkit.spec` | PyInstaller config (developers only). |
| `logo.ico` / `logo.png` | Application icon files. |

> ⚠️ **CRITICAL:** Do not move, rename, or delete `texconv.exe`. The DDS module requires it to be in the exact same folder as the main `atenea_toolkit.exe` executable to compress textures properly.

---

## 🎛️ Toolkit Modules (The Navigation Menu)

Atenea Toolkit unifies 3 independent utility tools into a single sidebar interface. Switch between them instantly depending on your current workflow:

### 1️⃣ Standard Converter
- **Purpose:** Batch format swapper for general images.
- **Ideal for:** Rapidly shifting large texture batches into high-efficiency formats like `.webp` or standard `.png` without changing dimensions.
- **Controls:** Includes an export quality slider for lossy formats (`JPG` / `WEBP`).

### 2️⃣ Image Resizer & Optimizer
- **Purpose:** Resolution scaling and canvas boundary management.
- **Ideal for:** Shrinking oversized assets to reduce server memory footprint and fix texture budget warnings (`physical memory pool`).
- **Controls:** Standard asset size presets (`128x128` up to `2048x2048`) and dynamic resolution-skipping logical filters.

### 3️⃣ DDS Studio (FiveM / GTA V)
- **Purpose:** Advanced game-ready texture compilation.
- **Ideal for:** Server developers, vehicle skinners, and MLO modders optimizing streams. Converts images into industry-standard block compression (`BC7`, `BC3`, `BC1`) with multi-level Mipmaps.
- **Controls:** Toggleable Mipmap generation to avoid texture flickering (headless textures) in-game.

---

## 🚀 How to Use

**Step 1 — Open the Program**
- Double-click `atenea_toolkit.exe`. 
- The Atenea Toolkit window will launch using its signature dark premium theme with gold accents.

**Step 2 — Pick Your Module**
- Look at the **Left Sidebar Panel**.
- Click on either **Standard Converter**, **DDS Studio (FiveM)**, or **Image Resizer** to swap the control dashboard.

**Step 3 — Load Target Textures**
- Click **Select Files / Folders** in the top common panel.
- Select one or multiple images (`PNG`, `JPG`, `WEBP`, `BMP`, `TIFF`, or `DDS`). 
- The target counter on the top right will display the total loaded files.

**Step 4 — Select Output Target**
- Click **Destination Folder**. 
- By default, if left unchanged, the program will automatically save outputs into the source directory of your first selected file.

**Step 5 — Adjust Module Settings**
- **In Converter:** Set your target format and drag the quality level slider.
- **In DDS Studio:** Select your compression profile (`BC7` is highly recommended for high-fidelity GTA V assets; `BC3` for legacy standards). Keep **Generate Mipmaps** active for game assets.
- **In Resizer:** Pick a size layout preset or keep the default grid. Toggle *"Don't upscale if image is already smaller"* to avoid stretching low-res files.

**Step 6 — Process**
- Click the golden **Process** button on the bottom right.
- Watch the real-time activity log box and progress tracker. A popup window summary will notify you upon successful batch completion.

---

## 🗂️ Supported Formats & Compression Matrices

| Format | Extensions | Transparency | Optimal Use Case |
|--------|------------|--------------|------------------|
| **PNG** | `.png` | ✅ Yes (Preserved) | UI Interfaces, NUI Scripts, High-res master source files. |
| **WEBP** | `.webp` | ✅ Yes (Preserved) | Web-based assets, Discord bots, Discord inventory icons. |
| **JPG** | `.jpg` / `.jpeg` | ❌ No (Turns White) | Backgrounds or textures completely devoid of alpha data. |
| **DDS** | `.dds` | ✅ Yes (Alpha block) | Native GTA V / FiveM streaming resources (`ytd` files). |
| **BMP / TIFF**| `.bmp` / `.tiff` | ⚠️ Limited | Legacy raw format imports. |

---

## ⚙️ Core Processing Logic & Mechanics

- **Proportional Constraints:** The Image Resizer scales images down perfectly without crushing or stretching aspect ratios. It centers smaller items into the chosen layout bounding box.
- **Asynchronous Execution:** All calculations run on background threads. The user interface will never freeze or show as *"Not Responding"* even while converting hundreds of high-res textures.
- **Console Feedback:** The built-in terminal logs specific details file-by-file, alerting you exactly which texture had an error or which file was skipped based on your active safety filters.

---

## 💡 Pro Tips for FiveM Server Optimization

- **The Gold Standard Chain:** For optimal server loading times and lower texture memory usage, use the **Image Resizer** first to bring heavy vehicle skins down to `1024x1024`, then pass them through the **DDS Studio** using `BC7` with **Mipmaps enabled** before importing into your `.ytd` files.
- **Mipmaps Warning:** Always leave Mipmaps enabled for map props (MLOs) and cars. Disabling them might save minor file space, but it causes severe aliasing and flickering textures when viewed from a distance in-game.

---

<div align="center">

© 2026 **Atenea Store Tools**

</div>
Discord: https://discord.gg/mam8Nmg49d

**IMAGES:**

![1](https://i.imgur.com/YkWM6W2.png)
![2](https://i.imgur.com/risTGGD.png)
![3](https://i.imgur.com/7w7XdIO.png)
![4](https://i.imgur.com/kvA37p2.png)
