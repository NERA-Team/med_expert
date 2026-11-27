import { app, BrowserWindow, screen } from 'electron';
import path from 'node:path';
import started from 'electron-squirrel-startup';
import * as storage from "electron-store";

if (started) {
    app.quit();
}


function calculateNineSixteenSize() {
    const primaryDisplay = screen.getPrimaryDisplay();
    const width = primaryDisplay.bounds.height * 0.5;
    const height = primaryDisplay.bounds.width * 0.5;
    
    return {
        width,
        height
    };
}

const createWindow = () => {
    const size = calculateNineSixteenSize();
    
    console.log(`Creating window with 9:16 ratio - Width: ${size.width}px, Height: ${size.height}px`); // ← для отладки
    
    const mainWindow = new BrowserWindow({
        width: size.width,
        height: size.height,
        
        minWidth: size.width * 0.85,
        minHeight: size.height * 0.85,
        
        webPreferences: {
            preload: path.join(__dirname, 'preload.cjs'),
        },
        
        center: true,  
        resizable: false,             
    });

    if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
        mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
    } else {
        mainWindow.loadFile(
            path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`),
        );
    }

    mainWindow.webContents.openDevTools();
};

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});
