const CELL_WIDTH = 192;
const CELL_HEIGHT = 208;

const STATES = {
  idle: { row: 0, label: "Idle", durations: [280, 110, 110, 140, 140, 320] },
  "running-right": {
    row: 1,
    label: "Run right",
    durations: [120, 120, 120, 120, 120, 120, 120, 220],
  },
  "running-left": {
    row: 2,
    label: "Run left",
    durations: [120, 120, 120, 120, 120, 120, 120, 220],
  },
  waving: { row: 3, label: "Wave", durations: [140, 140, 140, 280] },
  jumping: { row: 4, label: "Jump", durations: [140, 140, 140, 140, 280] },
  failed: {
    row: 5,
    label: "Failed",
    durations: [140, 140, 140, 140, 140, 140, 140, 240],
  },
  waiting: { row: 6, label: "Waiting", durations: [150, 150, 150, 150, 150, 260] },
  running: { row: 7, label: "Task running", durations: [120, 120, 120, 120, 120, 220] },
  review: { row: 8, label: "Review", durations: [150, 150, 150, 150, 150, 280] },
  look: {
    row: 9,
    label: "Look directions",
    durations: Array.from({ length: 16 }, () => 240),
  },
};

const DIRECTIONS = [
  "000° up",
  "022.5°",
  "045°",
  "067.5°",
  "090° right",
  "112.5°",
  "135°",
  "157.5°",
  "180° down",
  "202.5°",
  "225°",
  "247.5°",
  "270° left",
  "292.5°",
  "315°",
  "337.5°",
];

const atlas = new Image();
const reducedAtlas = new Image();
const heroCanvas = document.querySelector("#hero-canvas");
const labCanvas = document.querySelector("#lab-canvas");
const stateSelect = document.querySelector("#state");
const directionSelect = document.querySelector("#direction");
const directionBlock = document.querySelector("#direction-block");
const speedInput = document.querySelector("#speed");
const speedValue = document.querySelector("#speed-value");
const reduceMotion = document.querySelector("#reduce-motion");
const playButton = document.querySelector("#play");
const previousButton = document.querySelector("#previous");
const nextButton = document.querySelector("#next");
const frameReadout = document.querySelector("#frame-readout");
const heroStatus = document.querySelector("#hero-status");
const assetError = document.querySelector("#asset-error");
const systemReduced = window.matchMedia("(prefers-reduced-motion: reduce)");

let activeState = "idle";
let activeFrame = 0;
let heroFrame = 0;
let playing = true;
let timer = 0;
let heroTimer = 0;
let loaded = false;
let reducedLoaded = false;

for (const [index, label] of DIRECTIONS.entries()) {
  const option = document.createElement("option");
  option.value = String(index);
  option.textContent = label;
  directionSelect.append(option);
}

function cellFor(stateName, frame) {
  if (stateName !== "look") {
    return { row: STATES[stateName].row, column: frame };
  }
  return {
    row: frame < 8 ? 9 : 10,
    column: frame % 8,
  };
}

function draw(canvas, stateName, frame) {
  if (!loaded) return;
  const context = canvas.getContext("2d");
  const cell = cellFor(stateName, frame);
  const source = effectiveReducedMotion() && reducedLoaded ? reducedAtlas : atlas;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(
    source,
    cell.column * CELL_WIDTH,
    cell.row * CELL_HEIGHT,
    CELL_WIDTH,
    CELL_HEIGHT,
    0,
    0,
    canvas.width,
    canvas.height,
  );
}

function frameCount() {
  return STATES[activeState].durations.length;
}

function describeFrame() {
  if (activeState === "look") {
    frameReadout.textContent = `Look direction ${DIRECTIONS[activeFrame]}, pose ${activeFrame + 1} of 16`;
    return;
  }
  frameReadout.textContent =
    `${STATES[activeState].label}, frame ${activeFrame + 1} of ${frameCount()}`;
}

function renderLab() {
  draw(labCanvas, activeState, activeFrame);
  describeFrame();
}

function clearLabTimer() {
  if (timer) {
    window.clearTimeout(timer);
    timer = 0;
  }
}

function effectiveReducedMotion() {
  return reduceMotion.checked || systemReduced.matches;
}

function scheduleLab() {
  clearLabTimer();
  if (!playing || effectiveReducedMotion() || activeState === "look" || !loaded) {
    return;
  }
  const duration = STATES[activeState].durations[activeFrame] / Number(speedInput.value);
  timer = window.setTimeout(() => {
    activeFrame = (activeFrame + 1) % frameCount();
    renderLab();
    scheduleLab();
  }, duration);
}

function updatePlayLabel() {
  playButton.textContent = playing ? "Pause" : "Play";
  playButton.disabled = effectiveReducedMotion() || activeState === "look";
}

function resetState() {
  activeState = stateSelect.value;
  activeFrame = activeState === "look" ? Number(directionSelect.value) : 0;
  directionBlock.hidden = activeState !== "look";
  if (activeState === "look") {
    playing = false;
  }
  renderLab();
  updatePlayLabel();
  scheduleLab();
}

function scheduleHero() {
  if (heroTimer) window.clearTimeout(heroTimer);
  if (effectiveReducedMotion() || !loaded) {
    heroFrame = 0;
    draw(heroCanvas, "idle", heroFrame);
    return;
  }
  const durations = STATES.idle.durations;
  heroTimer = window.setTimeout(() => {
    heroFrame = (heroFrame + 1) % durations.length;
    draw(heroCanvas, "idle", heroFrame);
    scheduleHero();
  }, durations[heroFrame]);
}

stateSelect.addEventListener("change", resetState);
directionSelect.addEventListener("change", () => {
  activeFrame = Number(directionSelect.value);
  renderLab();
});
speedInput.addEventListener("input", () => {
  speedValue.value = `${Number(speedInput.value).toFixed(2).replace(/0$/, "")}×`;
  scheduleLab();
});
reduceMotion.addEventListener("change", () => {
  // The reduced atlas repeats a stable pose for animated rows but deliberately
  // preserves all sixteen look cells. Keep the selected frame/direction.
  renderLab();
  updatePlayLabel();
  scheduleLab();
  scheduleHero();
});
playButton.addEventListener("click", () => {
  playing = !playing;
  updatePlayLabel();
  scheduleLab();
});
previousButton.addEventListener("click", () => {
  activeFrame = (activeFrame - 1 + frameCount()) % frameCount();
  if (activeState === "look") directionSelect.value = String(activeFrame);
  renderLab();
  scheduleLab();
});
nextButton.addEventListener("click", () => {
  activeFrame = (activeFrame + 1) % frameCount();
  if (activeState === "look") directionSelect.value = String(activeFrame);
  renderLab();
  scheduleLab();
});
systemReduced.addEventListener("change", () => {
  // A system preference change must not silently change the chosen direction.
  renderLab();
  updatePlayLabel();
  scheduleLab();
  scheduleHero();
});

atlas.addEventListener("load", () => {
  if (atlas.naturalWidth !== 1536 || atlas.naturalHeight !== 2288) {
    heroStatus.textContent = "The atlas loaded with unexpected dimensions.";
    assetError.hidden = false;
    return;
  }
  loaded = true;
  document.body.classList.add("is-loaded");
  heroStatus.textContent = "Real release atlas, idle state.";
  renderLab();
  scheduleLab();
  scheduleHero();
});

atlas.addEventListener("error", () => {
  heroStatus.textContent = "The release atlas could not load.";
  assetError.hidden = false;
});

reducedAtlas.addEventListener("load", () => {
  if (reducedAtlas.naturalWidth !== 1536 || reducedAtlas.naturalHeight !== 2288) {
    return;
  }
  reducedLoaded = true;
  if (effectiveReducedMotion()) {
    renderLab();
    scheduleHero();
  }
});

reducedAtlas.addEventListener("error", () => {
  if (effectiveReducedMotion()) {
    heroStatus.textContent = "Reduced atlas unavailable; using a still frame from the original.";
  }
});

// Browsers can preserve form selections across reloads. Synchronize the
// internal state and visibility before either atlas starts loading.
resetState();

atlas.src = "spritesheet.webp";
reducedAtlas.src = "assets/momo-reduced.webp";
