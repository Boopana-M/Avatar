class ISLAvatarWidget {
  constructor(videoUrl) {
    this.videoUrl = videoUrl;
    this.container = null;
    this.canvas = null;
    
    // Three.js instances
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.avatar = null;
    this.bones = {}; // Maps generic names to actual THREE.Bone objects
    
    // Sync state
    this.animationData = [];
    this.videoElement = null;
    this.isPlaying = false;
    this.timeUpdateListener = null;
    this.animationFrameId = null;
    this.lastTime = -1;
  }

  init() {
    this.createDOM();
    this.initThreeJS();
    this.loadData();
    this.setupVideoSync();
    
    // Start animation loop
    this.animate();
  }

  createDOM() {
    // 1. Container
    this.container = document.createElement("div");
    this.container.className = "isl-avatar-container";
    
    // 2. Control Bar / Header
    const header = document.createElement("div");
    header.className = "isl-avatar-header";
    
    const title = document.createElement("div");
    title.className = "isl-avatar-title";
    title.innerHTML = "🤟 ISL Avatar";
    
    const closeBtn = document.createElement("button");
    closeBtn.className = "isl-avatar-close";
    closeBtn.innerHTML = "×";
    closeBtn.addEventListener("click", () => this.remove());
    
    header.appendChild(title);
    header.appendChild(closeBtn);
    this.container.appendChild(header);
    
    // 3. Canvas
    this.canvas = document.createElement("canvas");
    this.canvas.className = "isl-avatar-canvas";
    this.container.appendChild(this.canvas);
    
    // 4. Loading Overlay
    this.loader = document.createElement("div");
    this.loader.className = "isl-avatar-loader";
    
    const spinner = document.createElement("div");
    spinner.className = "isl-spinner";
    
    const loaderText = document.createElement("div");
    loaderText.className = "isl-loader-text";
    loaderText.innerText = "Extracting Captions...";
    
    const loaderSubtext = document.createElement("div");
    loaderSubtext.className = "isl-loader-subtext";
    loaderSubtext.innerText = "This might take a moment if ASR fallback runs.";
    
    this.loader.appendChild(spinner);
    this.loader.appendChild(loaderText);
    this.loader.appendChild(loaderSubtext);
    this.container.appendChild(this.loader);
    
    // Append to body
    document.body.appendChild(this.container);
  }

  setLoaderState(text, subtext = "") {
    if (this.loader) {
      const txtEl = this.loader.querySelector(".isl-loader-text");
      const subEl = this.loader.querySelector(".isl-loader-subtext");
      if (txtEl) txtEl.innerText = text;
      if (subEl) subEl.innerText = subtext;
    }
  }

  hideLoader() {
    if (this.loader) {
      this.loader.style.display = "none";
    }
  }

  showError(msg) {
    if (this.loader) {
      const spinner = this.loader.querySelector(".isl-spinner");
      if (spinner) spinner.style.display = "none";
      this.setLoaderState("Translation Error", msg);
      this.loader.querySelector(".isl-loader-text").style.color = "#ff3838";
    }
  }

  initThreeJS() {
    const width = 320;
    const height = 280;
    
    // Scene
    this.scene = new THREE.Scene();
    
    // Camera - focus on upper body (chest/head/hands)
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    this.camera.position.set(0, 1.35, 1.25);
    this.camera.lookAt(0, 1.35, 0);
    
    // Renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true // Transparent background
    });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.outputEncoding = THREE.sRGBEncoding;
    this.renderer.shadowMap.enabled = true;
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
    this.scene.add(ambientLight);
    
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(2, 4, 3);
    this.scene.add(dirLight);
    
    const dirLight2 = new THREE.DirectionalLight(0xa6d5ff, 0.3); // Soft blue rim light
    dirLight2.position.set(-2, 2, -2);
    this.scene.add(dirLight2);
  }

  loadData() {
    this.setLoaderState("Generating Gloss...", "Running English to ISL translator via local Ollama...");
    
    // Request translation from local FastAPI server
    fetch("http://localhost:8000/translate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ youtube_url: this.videoUrl })
    })
    .then(res => {
      if (!res.ok) throw new Error("Server responded with code " + res.status);
      return res.json();
    })
    .then(data => {
      if (data.status !== "success") throw new Error(data.detail || "Translation failed");
      
      this.animationData = data.animation_data;
      console.log(`[Overlay] Loaded ${this.animationData.length} frames of animation.`);
      
      // If unmatched words, display badge
      if (data.unmatched_words && data.unmatched_words.length > 0) {
        this.showUnmatchedBadge(data.unmatched_words);
      }
      
      // Load avatar model
      this.loadAvatarModel();
    })
    .catch(err => {
      console.error("[Overlay] Translation request failed:", err);
      this.showError(err.message + ". Make sure backend is running at http://localhost:8000");
    });
  }

  showUnmatchedBadge(words) {
    const badge = document.createElement("div");
    badge.className = "isl-unmatched-badge";
    badge.title = "These words do not have recorded signs in INCLUDE dataset: " + words.join(", ");
    badge.innerText = `⚠️ ${words.length} unmatched words`;
    this.container.appendChild(badge);
  }

  loadAvatarModel() {
    this.setLoaderState("Loading Avatar...", "Downloading GLB model from http://localhost:8000/models/avatar.glb");
    
    const loader = new THREE.GLTFLoader();
    const avatarUrl = "http://localhost:8000/models/avatar.glb";
    
    loader.load(avatarUrl, (gltf) => {
      this.avatar = gltf.scene;
      
      // Position character chest height
      this.avatar.position.set(0, 0, 0);
      this.scene.add(this.avatar);
      
      // Map skeleton bones
      this.mapSkeletonBones();
      
      this.hideLoader();
      console.log("[Overlay] Avatar model loaded successfully!");
    }, 
    (xhr) => {
      if (xhr.total > 0) {
        const percent = Math.round((xhr.loaded / xhr.total) * 100);
        this.setLoaderState("Loading Avatar...", `Downloaded ${percent}%`);
      }
    },
    (err) => {
      console.error("[Overlay] Failed to load avatar GLB:", err);
      this.showError("avatar.glb not found. Make sure models/avatar.glb exists on the backend server.");
    });
  }

  mapSkeletonBones() {
    const standardRPMBones = [
      "LeftArm", "LeftForeArm", "LeftHand",
      "RightArm", "RightForeArm", "RightHand",
      "LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3",
      "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3",
      "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3",
      "LeftHandRing1", "LeftHandRing2", "LeftHandRing3",
      "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3",
      "RightHandThumb1", "RightHandThumb2", "RightHandThumb3",
      "RightHandIndex1", "RightHandIndex2", "RightHandIndex3",
      "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3",
      "RightHandRing1", "RightHandRing2", "RightHandRing3",
      "RightHandPinky1", "RightHandPinky2", "RightHandPinky3"
    ];
    
    this.bones = {};
    
    this.avatar.traverse((child) => {
      if (child.isBone) {
        const boneName = child.name;
        // Search if this bone name contains any of the standard names case-insensitively
        for (const stdName of standardRPMBones) {
          if (boneName.toLowerCase().endsWith(stdName.toLowerCase()) || 
              boneName.toLowerCase().includes(stdName.toLowerCase())) {
            this.bones[stdName] = child;
          }
        }
      }
    });
    
    console.log(`[Overlay] Mapped ${Object.keys(this.bones).length} skeleton bones.`);
  }

  setupVideoSync() {
    this.videoElement = document.querySelector("video");
    if (!this.videoElement) {
      console.warn("[Overlay] Could not find YouTube video element.");
      return;
    }
    
    // Sync to video time changes
    this.timeUpdateListener = () => {
      if (this.videoElement) {
        const currentTime = this.videoElement.currentTime;
        this.updatePose(currentTime);
      }
    };
    
    this.videoElement.addEventListener("timeupdate", this.timeUpdateListener);
  }

  updatePose(currentTime) {
    if (this.animationData.length === 0 || !this.avatar) return;
    
    // Find animation frame closest to current time
    // Since animationData is sorted by time, we can binary search or simple sweep
    let bestFrame = null;
    let minDiff = Infinity;
    
    for (const frame of this.animationData) {
      const diff = Math.abs(frame.time - currentTime);
      if (diff < minDiff && diff < 0.5) { // Ensure within 0.5s of caption block
        minDiff = diff;
        bestFrame = frame;
      }
    }
    
    // Apply rotations
    if (bestFrame) {
      const rotations = bestFrame.rotations;
      for (const [boneKey, rotQuat] of Object.entries(rotations)) {
        // Map generic key to standard mapped bone name
        // The rotations dictionary keys match what was output by rig_mapper.py,
        // which matches the keys inside get_avatar_bone_names(), e.g. LeftArm, RightHandThumb1
        const bone = this.bones[boneKey];
        if (bone) {
          // Set bone rotation quaternion
          bone.quaternion.set(rotQuat[0], rotQuat[1], rotQuat[2], rotQuat[3]);
        }
      }
    } else {
      // Return to default T-pose (idle state) if no active sign frame is nearby
      this.resetToTPose();
    }
  }

  resetToTPose() {
    if (!this.bones) return;
    for (const bone of Object.values(this.bones)) {
      bone.quaternion.set(0, 0, 0, 1);
    }
  }

  animate() {
    this.animationFrameId = requestAnimationFrame(() => this.animate());
    
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  toggle() {
    if (this.container) {
      const isHidden = this.container.style.display === "none";
      this.container.style.display = isHidden ? "flex" : "none";
    }
  }

  remove() {
    // Stop animation loops
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }
    
    // Clean up event listeners
    if (this.videoElement && this.timeUpdateListener) {
      this.videoElement.removeEventListener("timeupdate", this.timeUpdateListener);
    }
    
    // Remove element
    if (this.container) {
      this.container.remove();
    }
    
    // Clean up WebGL
    if (this.renderer) {
      this.renderer.dispose();
    }
  }
}
