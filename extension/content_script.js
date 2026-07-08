// Content script to inject the button and handle coordination

let lastUrl = location.href;
let injectionInterval = null;

// Track active overlay
let activeOverlay = null;

function debugLog(msg) {
  console.log("[ISL ContentScript]", msg);
}

// Polling check to inject the button
function startInjectionMonitor() {
  if (injectionInterval) clearInterval(injectionInterval);
  
  injectionInterval = setInterval(() => {
    // Check if URL changed (YouTube SPA navigation)
    if (location.href !== lastUrl) {
      debugLog("URL changed, resetting state...");
      lastUrl = location.href;
      if (activeOverlay) {
        activeOverlay.remove();
        activeOverlay = null;
      }
    }
    
    // Inject button if on a video watch page
    if (location.pathname === "/watch") {
      injectButton();
    }
  }, 1500);
}

function injectButton() {
  // Check if button already exists
  if (document.getElementById("isl-avatar-btn")) {
    return;
  }
  
  // Find standard anchor elements below video title.
  // Standard watch metadata containers:
  // 1. #owner (next to channel owner)
  // 2. #top-row (action buttons container)
  const target = document.querySelector("#owner") || document.querySelector("#top-row");
  
  if (!target) {
    return; // Wait for element to render
  }
  
  debugLog("Target container found. Injecting button...");
  
  const button = document.createElement("button");
  button.id = "isl-avatar-btn";
  button.className = "isl-inject-button";
  button.innerHTML = "🤟 Use Avatar";
  
  button.addEventListener("click", () => {
    const videoUrl = window.location.href;
    debugLog("Clicked 'Use Avatar' for URL: " + videoUrl);
    
    // If overlay already exists, toggle it
    if (activeOverlay) {
      activeOverlay.toggle();
    } else {
      activeOverlay = new ISLAvatarWidget(videoUrl);
      activeOverlay.init();
    }
  });
  
  // Append next to the target element (channel subscribe block)
  target.appendChild(button);
  debugLog("Button successfully injected!");
}

// Listen for standard YouTube page navigate events
window.addEventListener("yt-navigate-finish", () => {
  debugLog("YouTube navigation finished.");
  if (location.pathname === "/watch") {
    setTimeout(injectButton, 1000);
  }
});

// Run monitor on load
startInjectionMonitor();
debugLog("Content script initialized.");
