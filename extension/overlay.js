// overlay.js

let scene, camera, renderer, clock;
let currentVrm = null;
let animationData = null;
let captionBlocks = null;
let currentVideoTime = 0.0;
let isPlaying = false;

const log = (msg) => {
  window.parent.postMessage({ type: "IFRAME_LOG", message: msg }, "*");
};

// Initialize Three.js WebGL rendering environment
function initThree() {
  const container = document.getElementById("canvas-container");
  
  scene = new THREE.Scene();
  
  // Set up camera focused on character's upper body (waist-up)
  camera = new THREE.PerspectiveCamera(35, container.clientWidth / container.clientHeight, 0.1, 20.0);
  camera.position.set(0.0, 1.25, 0.95);
  camera.lookAt(0.0, 1.2, 0.0);
  
  // Set up renderer with transparent background and antialiasing
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.shadowMap.enabled = true;
  container.appendChild(renderer.domElement);
  
  // Set up lighting (vibrant and clear to highlight hand movements)
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);
  
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(2.0, 4.0, 3.0);
  scene.add(dirLight);
  
  const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
  fillLight.position.set(-2.0, 2.0, 2.0);
  scene.add(fillLight);
  
  clock = new THREE.Clock();
  
  // Start animate loop
  animate();
  
  // Handle window resizing
  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });
}

// Render loop
function animate() {
  requestAnimationFrame(animate);
  
  const delta = clock.getDelta();
  if (currentVrm) {
    currentVrm.update(delta);
    
    // Apply animation rotations based on current play position
    applyAnimationPose(currentVideoTime);
  }
  
  renderer.render(scene, camera);
}

// Set up bone reference cache for instant access
let boneNodesCache = {};
function getBoneNode(boneName) {
  if (boneNodesCache[boneName]) {
    return boneNodesCache[boneName];
  }
  const node = scene.getObjectByName(boneName);
  if (node) {
    boneNodesCache[boneName] = node;
  }
  return node;
}

// Resets character back to the default rest pose
function setRestPose() {
  if (!currentVrm) return;
  // Apply identity or rest pose values
  const upperLeftArm = getBoneNode("J_Bip_L_UpperArm");
  const upperRightArm = getBoneNode("J_Bip_R_UpperArm");
  const lowerLeftArm = getBoneNode("J_Bip_L_LowerArm");
  const lowerRightArm = getBoneNode("J_Bip_R_LowerArm");
  
  if (upperLeftArm) upperLeftArm.quaternion.set(0.0, 0.0, -0.64279, 0.76604);
  if (upperRightArm) upperRightArm.quaternion.set(0.0, 0.0, 0.64279, 0.76604);
  if (lowerLeftArm) lowerLeftArm.quaternion.set(0.0, 0.17365, 0.0, 0.98481);
  if (lowerRightArm) lowerRightArm.quaternion.set(0.0, -0.17365, 0.0, 0.98481);
}

// Find close animation frame and update joints
function applyAnimationPose(time) {
  if (!animationData || !animationData.frames || animationData.frames.length === 0) {
    return;
  }
  
  const fps = animationData.fps || 30;
  let frameIdx = Math.round(time * fps);
  
  // Clamp frame index
  if (frameIdx < 0) frameIdx = 0;
  if (frameIdx >= animationData.frames.length) {
    frameIdx = animationData.frames.length - 1;
  }
  
  const frame = animationData.frames[frameIdx];
  if (frame && frame.rotations) {
    // Apply each bone rotation
    for (const [boneName, q] of Object.entries(frame.rotations)) {
      const boneNode = getBoneNode(boneName);
      if (boneNode) {
        boneNode.quaternion.set(q[0], q[1], q[2], q[3]);
      }
    }
  }
  
  // Update HUD text (Gloss / active words)
  updateHUD(time);
}

// Update text display in HUD based on video time
function updateHUD(time) {
  if (!captionBlocks) return;
  
  let activeBlock = null;
  for (const block of captionBlocks) {
    if (time >= block.start && time <= block.end) {
      activeBlock = block;
      break;
    }
  }
  
  const wordTextEl = document.getElementById("word-text");
  const wordTierEl = document.getElementById("word-tier");
  const statusIndicatorEl = document.getElementById("status-indicator");
  const statusTextEl = document.getElementById("status-text");
  
  if (isPlaying) {
    statusIndicatorEl.className = "status-indicator active";
    statusTextEl.innerText = "SIGNING";
  } else {
    statusIndicatorEl.className = "status-indicator";
    statusTextEl.innerText = "PAUSED";
  }

  if (activeBlock) {
    // Determine which gloss word is active based on time elapsed in block
    const words = activeBlock.words || [];
    if (words.length > 0) {
      const duration = activeBlock.end - activeBlock.start;
      const elapsed = time - activeBlock.start;
      const wordIdx = Math.min(
        words.length - 1,
        Math.floor((elapsed / duration) * words.length)
      );
      
      const activeWord = words[wordIdx];
      const wordStr = activeWord.word || "";
      const source = activeWord.source || "unmatched";
      const tier = activeWord.tier || 3;
      
      wordTextEl.innerText = wordStr;
      wordTierEl.style.display = "inline-block";
      
      if (source === "fingerspelling") {
        wordTierEl.className = "word-tier tier-spell";
        wordTierEl.innerText = "Fingerspell (A-Z)";
      } else if (source === "unmatched") {
        wordTierEl.className = "word-tier tier-none";
        wordTierEl.innerText = "Unmatched";
      } else if (tier === 1) {
        wordTierEl.className = "word-tier tier-exact";
        wordTierEl.innerText = "Tier 1: Exact Sign";
      } else {
        wordTierEl.className = "word-tier tier-lemma";
        wordTierEl.innerText = "Tier 2: Lemma Sign";
      }
    } else {
      wordTextEl.innerText = activeBlock.text || "--";
      wordTierEl.style.display = "none";
    }
  } else {
    wordTextEl.innerText = "Idle";
    wordTierEl.style.display = "none";
  }
}

// Load VRM Avatar using GLTFLoader and THREE_VRM.VRMLoaderPlugin
function loadAvatar() {
  const msgEl = document.getElementById("loading-message");
  msgEl.innerText = "Loading 3D Rig (avatar.vrm)...";
  
  try {
    if (typeof THREE.GLTFLoader === "undefined") {
      throw new Error("THREE.GLTFLoader is not defined. Ensure GLTFLoader.js is loaded correctly.");
    }
    if (typeof THREE_VRM === "undefined" || typeof THREE_VRM.VRMLoaderPlugin === "undefined") {
      throw new Error("THREE_VRM.VRMLoaderPlugin is not defined. Ensure three-vrm.js v1.x+ is loaded correctly.");
    }

    const loader = new THREE.GLTFLoader();
    
    // Register VRMLoaderPlugin to handle VRM extensions (VRMC_vrm)
    loader.register((parser) => {
      return new THREE_VRM.VRMLoaderPlugin(parser);
    });

    loader.load(
      "http://localhost:8000/avatar.vrm",
      (gltf) => {
        try {
          msgEl.innerText = "Initializing VRM Humanoid bones...";
          
          // Retrieve the VRM instance from gltf.userData
          const vrm = gltf.userData.vrm;
          if (!vrm) {
            throw new Error("VRM instance not found in GLTF user data. Verify file integrity.");
          }
          
          scene.add(vrm.scene);
          currentVrm = vrm;
          vrm.scene.rotation.y = 0.0; // Face the camera
          
          // Reset arms to resting pose
          setRestPose();
          
          log("VRM model loaded successfully.");
          checkInitializationComplete();
        } catch (innerErr) {
          msgEl.innerText = "VRM Initialization Error: " + innerErr.message;
          log("VRM Initialization failed: " + innerErr);
        }
      },
      (xhr) => {
        if (xhr.total) {
          const pct = Math.round((xhr.loaded / xhr.total) * 100);
          msgEl.innerText = `Downloading Avatar Model: ${pct}%`;
        }
      },
      (err) => {
        msgEl.innerText = "Network Error loading VRM model. Make sure backend port 8000 is active.";
        log("Network error loading VRM: " + err);
      }
    );
  } catch (err) {
    msgEl.innerText = "Failed to initiate avatar loader: " + err.message;
    log("Loader initialization error: " + err);
  }
}

let isVrmReady = false;
let isPipelineReady = false;

function checkInitializationComplete() {
  const msgEl = document.getElementById("loading-message");
  
  if (currentVrm) {
    isVrmReady = true;
  }
  
  if (animationData) {
    isPipelineReady = true;
  }
  
  if (isVrmReady && isPipelineReady) {
    // Fade out overlay
    const overlay = document.getElementById("loading-overlay");
    overlay.style.opacity = 0;
    setTimeout(() => {
      overlay.style.display = "none";
    }, 500);
    
    // Set active status indicator
    document.getElementById("status-indicator").className = "status-indicator active";
    document.getElementById("status-text").innerText = "ACTIVE";
  } else if (isVrmReady) {
    msgEl.innerText = "Waiting for backend transcription & translation...";
  }
}

let pollInterval = null;
let receivedBlockIndices = new Set();
let videoId = null;

// Fetch ISL translation pipeline from FastAPI backend
function fetchTranslation(videoUrl) {
  const msgEl = document.getElementById("loading-message");
  msgEl.innerText = "Querying backend translation pipeline (ASR/Captions/Gloss)...";
  
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  receivedBlockIndices.clear();
  videoId = null;

  fetch("http://localhost:8000/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoUrl })
  })
  .then(res => {
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return res.json();
  })
  .then(data => {
    videoId = data.video_id;
    
    if (data.status === "completed") {
      animationData = data.animation_data;
      captionBlocks = data.caption_blocks || [];
      log("Translation pipeline loaded from cache. Animation timeline ready.");
      checkInitializationComplete();
    } else {
      if (data.caption_blocks && data.caption_blocks.length > 0) {
        handleInitialCaptionBlocks(data.caption_blocks);
      } else {
        msgEl.innerText = "Waiting for backend transcription & translation...";
      }
      startPolling();
    }
  })
  .catch(err => {
    msgEl.innerText = "Error in Translation Pipeline: " + err.message + "\n(Verify Ollama is active & backend running)";
    log("Translation request failed: " + err);
  });
}

function handleInitialCaptionBlocks(blocks) {
  captionBlocks = blocks;
  
  // Pre-allocate blank frames based on the last caption end time
  const fps = 30;
  const lastBlock = captionBlocks[captionBlocks.length - 1];
  const totalDuration = lastBlock ? (lastBlock.end + 3.0) : 10.0;
  
  // Initialize JS rest pose
  const JS_REST_POSE = {
    "J_Bip_L_UpperArm": [0.0, 0.0, -0.64279, 0.76604],
    "J_Bip_R_UpperArm": [0.0, 0.0, 0.64279, 0.76604],
    "J_Bip_L_LowerArm": [0.0, 0.17365, 0.0, 0.98481],
    "J_Bip_R_LowerArm": [0.0, -0.17365, 0.0, 0.98481],
    "J_Bip_L_Hand": [0.0, 0.0, 0.0, 1.0],
    "J_Bip_R_Hand": [0.0, 0.0, 0.0, 1.0]
  };
  const fingers = ["Thumb", "Index", "Middle", "Ring", "Little"];
  for (const f of fingers) {
    for (let suffix of ["1", "2", "3"]) {
      JS_REST_POSE[`J_Bip_L_${f}${suffix}`] = [0.0, 0.0, 0.0, 1.0];
      JS_REST_POSE[`J_Bip_R_${f}${suffix}`] = [0.0, 0.0, 0.0, 1.0];
    }
  }

  const totalFrames = Math.round(totalDuration * fps);
  const blankFrames = [];
  for (let i = 0; i < totalFrames; i++) {
    blankFrames.push({
      time: i / fps,
      rotations: JSON.parse(JSON.stringify(JS_REST_POSE))
    });
  }
  
  animationData = {
    fps: fps,
    duration: totalDuration,
    frames: blankFrames
  };
  
  log(`Pre-allocated ${totalFrames} frames for progressive updates.`);
  checkInitializationComplete();
}

function startPolling() {
  if (pollInterval) return;
  
  pollInterval = setInterval(() => {
    if (!videoId) return;
    
    const receivedStr = Array.from(receivedBlockIndices).join(",");
    fetch(`http://localhost:8000/translate/status?video_id=${videoId}&received_blocks=${receivedStr}`)
    .then(res => {
      if (!res.ok) throw new Error("Status check failed");
      return res.json();
    })
    .then(data => {
      if (data.caption_blocks && (!captionBlocks || captionBlocks.length === 0)) {
        handleInitialCaptionBlocks(data.caption_blocks);
      }
      
      // Process new blocks
      if (data.new_blocks && data.new_blocks.length > 0) {
        data.new_blocks.forEach(block => {
          receivedBlockIndices.add(block.block_idx);
          
          if (block.frames && animationData) {
            const fps = animationData.fps || 30;
            block.frames.forEach(frame => {
              const frameIdx = Math.round(frame.time * fps);
              if (frameIdx >= 0 && frameIdx < animationData.frames.length) {
                animationData.frames[frameIdx].rotations = frame.rotations;
              }
            });
          }
          
          if (captionBlocks && captionBlocks[block.block_idx]) {
            captionBlocks[block.block_idx].words = block.words;
          }
          
          log(`Progressive update: Applied animation for caption block ${block.block_idx}`);
        });
      }
      
      if (data.status === "completed") {
        log("Progressive translation fully completed.");
        clearInterval(pollInterval);
        pollInterval = null;
      } else if (data.status === "failed") {
        log(`Backend task failed: ${data.error}`);
        clearInterval(pollInterval);
        pollInterval = null;
        const msgEl = document.getElementById("loading-message");
        if (msgEl) {
          msgEl.innerText = "Error in Translation Pipeline: " + data.error;
        }
      }
    })
    .catch(err => {
      log("Error during polling: " + err);
    });
  }, 2000);
}

// Listen to sync messages from content_script
window.addEventListener("message", (event) => {
  const data = event.data;
  if (!data) return;
  
  if (data.type === "INIT") {
    log(`Initializing iframe for URL: ${data.videoUrl}`);
    initThree();
    loadAvatar();
    fetchTranslation(data.videoUrl);
  } else if (data.type === "SYNC") {
    currentVideoTime = data.time;
    isPlaying = data.playing;
  }
});
