// content_script.js

let avatarIframe = null;
let syncInterval = null;
let currentVideoId = "";

// Helper to extract video ID from URL
function getVideoId() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get("v") || "";
}

// Inject "Use avatar" button near YouTube controls
function injectButton() {
  // Check if button already exists
  if (document.getElementById("isl-avatar-toggle-btn")) {
    return;
  }

  // Look for YouTube player right controls
  const controls = document.querySelector(".ytp-right-controls");
  if (!controls) {
    // If not loaded yet, retry
    setTimeout(injectButton, 1000);
    return;
  }

  // Create a button
  const button = document.createElement("button");
  button.id = "isl-avatar-toggle-btn";
  button.className = "ytp-button";
  button.title = "Use ISL Avatar Interpreter";
  button.style.verticalAlign = "middle";
  button.style.padding = "0 8px";
  
  // High quality SVG icon (stylized sign-language hands)
  button.innerHTML = `
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="#fff" style="pointer-events: none;">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15.5h-2v-2h2v2zm0-4h-2V7h2v6.5z"/>
    </svg>
  `;

  button.addEventListener("click", () => {
    toggleAvatar();
  });

  // Insert before the first child of right controls (typically the settings or fullscreen button)
  controls.insertBefore(button, controls.firstChild);
  console.log("[ISL Extension] Injected Use Avatar button successfully.");
}

// Toggle floating overlay
function toggleAvatar() {
  if (avatarIframe) {
    removeAvatar();
  } else {
    createAvatar();
  }
}

function createAvatar() {
  const videoElement = document.querySelector("video");
  const playerElement = document.querySelector("#movie_player") || document.querySelector(".html5-video-player");
  
  if (!videoElement) {
    alert("No YouTube video player found on this page.");
    return;
  }

  console.log("[ISL Extension] Creating Avatar Iframe...");

  // Create iframe element
  avatarIframe = document.createElement("iframe");
  avatarIframe.id = "isl-avatar-iframe";
  avatarIframe.src = chrome.runtime.getURL("overlay.html");
  
  // Style overlay box (glassmorphic dark design)
  avatarIframe.style.position = "absolute";
  avatarIframe.style.bottom = "60px";
  avatarIframe.style.right = "20px";
  avatarIframe.style.width = "250px";
  avatarIframe.style.height = "320px";
  avatarIframe.style.border = "none";
  avatarIframe.style.borderRadius = "12px";
  avatarIframe.style.boxShadow = "0 8px 32px 0 rgba(0, 0, 0, 0.5)";
  avatarIframe.style.backgroundColor = "rgba(18, 18, 18, 0.9)";
  avatarIframe.style.zIndex = "1000";
  avatarIframe.style.transition = "opacity 0.3s ease";
  avatarIframe.style.overflow = "hidden";

  // Append to player so it stays when player goes full-screen
  if (playerElement) {
    playerElement.appendChild(avatarIframe);
  } else {
    document.body.appendChild(avatarIframe);
    avatarIframe.style.position = "fixed";
  }

  // Once iframe is loaded, send init configurations
  avatarIframe.addEventListener("load", () => {
    const videoUrl = window.location.href;
    currentVideoId = getVideoId();
    
    avatarIframe.contentWindow.postMessage({
      type: "INIT",
      videoUrl: videoUrl
    }, "*");

    // Start synchronization loops
    startSync(videoElement);
  });

  // Update button active state if needed (change color)
  const btn = document.getElementById("isl-avatar-toggle-btn");
  if (btn) {
    btn.querySelector("svg").setAttribute("fill", "#00adb5");
  }
}

function removeAvatar() {
  if (avatarIframe) {
    avatarIframe.remove();
    avatarIframe = null;
  }
  stopSync();
  const btn = document.getElementById("isl-avatar-toggle-btn");
  if (btn) {
    btn.querySelector("svg").setAttribute("fill", "#ffffff");
  }
}

function startSync(videoElement) {
  stopSync();
  
  const sendSyncMsg = () => {
    if (avatarIframe && avatarIframe.contentWindow) {
      avatarIframe.contentWindow.postMessage({
        type: "SYNC",
        time: videoElement.currentTime,
        playing: !videoElement.paused,
        playbackRate: videoElement.playbackRate
      }, "*");
    }
  };

  // Sync on standard video events
  videoElement.addEventListener("timeupdate", sendSyncMsg);
  videoElement.addEventListener("play", sendSyncMsg);
  videoElement.addEventListener("pause", sendSyncMsg);
  videoElement.addEventListener("seeking", sendSyncMsg);
  videoElement.addEventListener("ratechange", sendSyncMsg);

  // Interval backup for precision sync (every 100ms)
  syncInterval = setInterval(sendSyncMsg, 100);
}

function stopSync() {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
}

// Watch for video navigation (YouTube client-side navigation)
function watchNavigation() {
  let lastUrl = window.location.href;
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      
      // If video changed, re-initialize button and remove previous avatar
      const newVideoId = getVideoId();
      if (newVideoId !== currentVideoId) {
        removeAvatar();
        setTimeout(injectButton, 1000);
      }
    }
  }, 1000);
}

// Initialize on page load
function init() {
  injectButton();
  watchNavigation();
  
  // Handle messages from the iframe (e.g. logging or resizing)
  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "IFRAME_LOG") {
      console.log("[ISL Overlay]", event.data.message);
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
