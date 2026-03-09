/**
 * carousel-generator.js — Data-driven carousel slide generator
 *
 * Reads a JSON data file and produces a branded PPTX carousel.
 * Brand, helpers, and slide patterns are adapted from carousel-template-v2.js
 * (which remains unchanged as a reference).
 *
 * Usage:
 *   node carousel-generator.js <path-to-data.json>
 *
 * The JSON must conform to carousel-data-schema.json.
 * Output is written to the directory specified in data.output_path
 * (default: substack/output/current/carousels/).
 */

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaBolt, FaChartBar, FaShieldAlt, FaLightbulb, FaChartLine } = require("react-icons/fa");

// ---------------------------------------------------------------------------
// Icon mapping — JSON data references icons by string name
// ---------------------------------------------------------------------------
const ICON_MAP = {
  bolt: FaBolt,
  chart_bar: FaChartBar,
  shield: FaShieldAlt,
  lightbulb: FaLightbulb,
  chart_line: FaChartLine,
};

// ---------------------------------------------------------------------------
// Asset generation (reused from carousel-template-v2.js lines 7-51)
// ---------------------------------------------------------------------------

function renderIconSvg(IconComponent, color, size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}

async function iconToBase64Png(IconComponent, color, size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

async function generateGridPattern(color, opacity, size = 800) {
  let lines = "";
  const step = 40;
  for (let i = 0; i <= size; i += step) {
    lines += `<line x1="${i}" y1="0" x2="${i}" y2="${size}" stroke="${color}" stroke-width="0.5" opacity="${opacity}"/>`;
    lines += `<line x1="0" y1="${i}" x2="${size}" y2="${i}" stroke="${color}" stroke-width="0.5" opacity="${opacity}"/>`;
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${lines}</svg>`;
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

async function generateSignalLine(color, width = 1200, height = 120) {
  const mid = height / 2;
  const points = [];
  for (let x = 0; x < width; x += 2) {
    let y = mid;
    const pct = x / width;
    if (pct > 0.3 && pct < 0.7) {
      const localPct = (pct - 0.3) / 0.4;
      y = mid - Math.sin(localPct * Math.PI * 4) * (mid * 0.7) * Math.exp(-Math.abs(localPct - 0.5) * 4);
    }
    points.push(`${x},${y.toFixed(1)}`);
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
    <polyline points="${points.join(" ")}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

// ---------------------------------------------------------------------------
// Brand constants (reused from carousel-template-v2.js lines 61-75)
// ---------------------------------------------------------------------------
const NAVY = "0F1B2D";
const DEEP_BLUE = "162B44";
const MID_BLUE = "1E3A5F";
const STEEL = "3D5A80";
const ICE = "E0E8F0";
const LIGHT_BG = "F5F7FA";
const WHITE = "FFFFFF";
const GOLD = "C9A84C";
const LIGHT_GOLD = "D4B96A";
const MUTED = "7A8B9E";
const DARK_TEXT = "0F1B2D";
const BODY_TEXT = "2C3E50";

const HEADER_FONT = "Georgia";
const BODY_FONT = "Calibri";

// ---------------------------------------------------------------------------
// Header + Footer helpers (reused from carousel-template-v2.js lines 88-127)
// ---------------------------------------------------------------------------

function addHeader(pres, slide, isDark = false) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: isDark ? NAVY : NAVY },
  });
  slide.addText("STERLING SIGNALS", {
    x: 0.6, y: 0.1, w: 4, h: 0.55,
    fontFace: BODY_FONT, fontSize: 14, color: WHITE,
    bold: true, charSpacing: 5, valign: "middle", margin: 0,
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.75, w: 10, h: 0.04,
    fill: { color: GOLD },
  });
}

function addFooter(pres, slide, pageNum, isDark = false) {
  const footY = 9.2;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: footY, w: 8.8, h: 0.01,
    fill: { color: isDark ? STEEL : ICE },
  });
  slide.addText("sterlingsignals.co", {
    x: 0.6, y: footY + 0.15, w: 4, h: 0.4,
    fontFace: BODY_FONT, fontSize: 10, color: isDark ? STEEL : MUTED,
    margin: 0,
  });
  slide.addText(String(pageNum).padStart(2, "0"), {
    x: 7.8, y: footY + 0.15, w: 1.6, h: 0.4,
    fontFace: BODY_FONT, fontSize: 11, color: isDark ? STEEL : MUTED,
    align: "right", margin: 0,
  });
}

// ---------------------------------------------------------------------------
// Shared slide heading helper
// ---------------------------------------------------------------------------

function addSlideHeading(slide, heading, iconData) {
  if (iconData) {
    slide.addImage({ data: iconData, x: 0.7, y: 1.2, w: 0.5, h: 0.5 });
  }
  const textX = iconData ? 1.4 : 0.7;
  slide.addText(heading, {
    x: textX, y: 1.15, w: 8, h: 0.6,
    fontFace: HEADER_FONT, fontSize: 30, color: DARK_TEXT,
    bold: true, margin: 0,
  });
  slide.addShape("rect", {
    x: 0.7, y: 1.95, w: 2.5, h: 0.04,
    fill: { color: GOLD },
  });
}

function addDarkSlideHeading(slide, heading, iconData) {
  if (iconData) {
    slide.addImage({ data: iconData, x: 0.7, y: 1.2, w: 0.5, h: 0.5 });
  }
  const textX = iconData ? 1.4 : 0.7;
  slide.addText(heading, {
    x: textX, y: 1.15, w: 8, h: 0.6,
    fontFace: HEADER_FONT, fontSize: 30, color: WHITE,
    bold: true, margin: 0,
  });
  slide.addShape("rect", {
    x: 0.7, y: 1.95, w: 2.5, h: 0.04,
    fill: { color: GOLD },
  });
}

// ---------------------------------------------------------------------------
// Resolve icon name → pre-generated base64 PNG data
// ---------------------------------------------------------------------------

function resolveIcon(iconName, assets) {
  if (!iconName) return null;
  return assets.icons[iconName] || null;
}

// ---------------------------------------------------------------------------
// SLIDE BUILDERS
// ---------------------------------------------------------------------------

function buildTitleSlide(pres, data, assets) {
  const slide = pres.addSlide();
  slide.background = { color: NAVY };

  // Grid overlay
  slide.addImage({ data: assets.gridPattern, x: 0, y: 0, w: 10, h: 10, transparency: 80 });

  // Header bar (DEEP_BLUE variant for title)
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: DEEP_BLUE },
  });
  slide.addText("STERLING SIGNALS", {
    x: 0.6, y: 0.1, w: 4, h: 0.55,
    fontFace: BODY_FONT, fontSize: 14, color: GOLD,
    bold: true, charSpacing: 5, valign: "middle", margin: 0,
  });
  // Series tag
  slide.addImage({ data: assets.icons.chart_line || assets.chartLineIcon, x: 5.4, y: 0.15, w: 0.4, h: 0.4 });
  slide.addText(data.series_tag || "MACRO PULSE", {
    x: 5.85, y: 0.1, w: 3, h: 0.55,
    fontFace: BODY_FONT, fontSize: 11, color: MUTED,
    charSpacing: 3, valign: "middle", margin: 0,
  });
  // Gold accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.75, w: 10, h: 0.04,
    fill: { color: GOLD },
  });

  // Signal pulse decoration
  slide.addImage({ data: assets.signalLineWhite, x: 0.5, y: 2.2, w: 9, h: 0.9, transparency: 85 });

  // Main title — split into lines, last line gold
  const titleLines = (data.title || "").split("\n");
  const titleParts = titleLines.map((line, i) => ({
    text: line,
    options: {
      breakLine: i < titleLines.length - 1,
      color: i < titleLines.length - 1 ? WHITE : GOLD,
    },
  }));
  slide.addText(titleParts, {
    x: 0.8, y: 3.0, w: 8.4, h: 3.0,
    fontFace: HEADER_FONT, fontSize: 60, bold: true,
    align: "center", valign: "middle",
    lineSpacingMultiple: 1.1, margin: 0,
  });

  // Subtitle
  if (data.subtitle) {
    slide.addText(data.subtitle, {
      x: 1.5, y: 6.2, w: 7, h: 0.6,
      fontFace: BODY_FONT, fontSize: 18, color: MUTED,
      align: "center", margin: 0,
    });
  }

  // Date tag
  if (data.date) {
    slide.addText(data.date, {
      x: 3.5, y: 7.2, w: 3, h: 0.4,
      fontFace: BODY_FONT, fontSize: 12, color: STEEL,
      align: "center", charSpacing: 3, margin: 0,
    });
  }

  // Swipe indicator
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 3.8, y: 8.4, w: 2.4, h: 0.45,
    fill: { color: DEEP_BLUE },
    line: { color: STEEL, width: 0.8 },
  });
  slide.addText("SWIPE \u2192", {
    x: 3.8, y: 8.4, w: 2.4, h: 0.45,
    fontFace: BODY_FONT, fontSize: 10, color: MUTED,
    charSpacing: 3, align: "center", valign: "middle", margin: 0,
  });

  addFooter(pres, slide, 1, true);
}

function buildContextSlide(pres, slideData, assets, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  addHeader(pres, slide);

  const iconData = resolveIcon(slideData.icon, assets);
  addSlideHeading(slide, slideData.heading, iconData);

  // Paragraphs
  const textParts = (slideData.paragraphs || []).map((para, i, arr) => ({
    text: para,
    options: {
      breakLine: i < arr.length - 1,
      paraSpaceAfter: 16,
      bold: i === arr.length - 1 && !slideData.callout, // bold last para if no callout
      color: i === arr.length - 1 && !slideData.callout ? DARK_TEXT : BODY_TEXT,
    },
  }));

  const calloutHeight = slideData.callout ? 1.5 : 0;
  const textAreaHeight = calloutHeight ? 4.0 : 5.5;

  slide.addText(textParts, {
    x: 0.7, y: 2.4, w: 8.6, h: textAreaHeight,
    fontFace: BODY_FONT, fontSize: 19, color: BODY_TEXT,
    lineSpacingMultiple: 1.4, margin: 0,
  });

  // Callout box
  if (slideData.callout) {
    const calloutY = 7.0;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: calloutY, w: 8.6, h: 1.5,
      fill: { color: WHITE },
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: calloutY, w: 0.06, h: 1.5,
      fill: { color: GOLD },
    });
    slide.addText(slideData.callout, {
      x: 1.15, y: calloutY, w: 7.8, h: 1.5,
      fontFace: HEADER_FONT, fontSize: 16, color: STEEL,
      italic: true, valign: "middle", margin: 0,
    });
  }

  addFooter(pres, slide, pageNum);
}

function buildStatsSlide(pres, slideData, assets, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  addHeader(pres, slide);

  const iconData = resolveIcon(slideData.icon, assets);
  addSlideHeading(slide, slideData.heading, iconData);

  // 2×2 grid layout
  const positions = [
    { x: 0.7, y: 2.4 },   // top-left
    { x: 5.2, y: 2.4 },   // top-right
    { x: 0.7, y: 5.5 },   // bottom-left
    { x: 5.2, y: 5.5 },   // bottom-right
  ];

  const items = slideData.items || [];
  for (let i = 0; i < Math.min(items.length, 4); i++) {
    const stat = items[i];
    const pos = positions[i];

    // Card
    slide.addShape(pres.shapes.RECTANGLE, {
      x: pos.x, y: pos.y, w: 4.1, h: 2.6,
      fill: { color: WHITE },
      shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.06 },
    });
    // Gold top accent
    slide.addShape(pres.shapes.RECTANGLE, {
      x: pos.x, y: pos.y, w: 4.1, h: 0.05,
      fill: { color: GOLD },
    });
    // Number
    slide.addText(stat.number, {
      x: pos.x + 0.45, y: pos.y + 0.35, w: 3.2, h: 1.0,
      fontFace: HEADER_FONT, fontSize: 40, color: MID_BLUE,
      bold: true, margin: 0,
    });
    // Label
    slide.addText(stat.label, {
      x: pos.x + 0.45, y: pos.y + 1.35, w: 3.2, h: 1.0,
      fontFace: BODY_FONT, fontSize: 15, color: MUTED,
      margin: 0, lineSpacingMultiple: 1.25,
    });
  }

  addFooter(pres, slide, pageNum);
}

function buildTwoColumnSlide(pres, slideData, assets, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  addHeader(pres, slide);

  const iconData = resolveIcon(slideData.icon, assets);
  addSlideHeading(slide, slideData.heading, iconData);

  // Build a column helper
  function addColumn(colData, startX) {
    // Card
    slide.addShape(pres.shapes.RECTANGLE, {
      x: startX, y: 2.4, w: 4.1, h: 6.2,
      fill: { color: WHITE },
      shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.06 },
    });
    // Color top bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: startX, y: 2.4, w: 4.1, h: 0.05,
      fill: { color: colData.color },
    });
    // Column title
    slide.addText(colData.title, {
      x: startX, y: 2.7, w: 4.1, h: 0.45,
      fontFace: BODY_FONT, fontSize: 12, color: colData.color,
      bold: true, charSpacing: 4, align: "center", margin: 0,
    });
    // Items as bullets
    const bulletItems = (colData.items || []).map((item, i, arr) => ({
      text: item,
      options: {
        bullet: true,
        breakLine: i < arr.length - 1,
        paraSpaceAfter: 12,
        color: BODY_TEXT,
      },
    }));
    slide.addText(bulletItems, {
      x: startX + 0.5, y: 3.4, w: 3.2, h: 4.8,
      valign: "top",
      fontFace: BODY_FONT, fontSize: 15, lineSpacingMultiple: 1.35, margin: 0,
    });
  }

  if (slideData.left) addColumn(slideData.left, 0.7);
  if (slideData.right) addColumn(slideData.right, 5.2);

  addFooter(pres, slide, pageNum);
}

function buildTakeawaySlide(pres, slideData, assets, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: NAVY };

  // Grid overlay
  slide.addImage({ data: assets.gridPattern, x: 0, y: 0, w: 10, h: 10, transparency: 85 });

  // Dark header (DEEP_BLUE variant)
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: DEEP_BLUE },
  });
  slide.addText("STERLING SIGNALS", {
    x: 0.6, y: 0.1, w: 4, h: 0.55,
    fontFace: BODY_FONT, fontSize: 14, color: GOLD,
    bold: true, charSpacing: 5, valign: "middle", margin: 0,
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.75, w: 10, h: 0.04,
    fill: { color: GOLD },
  });

  const iconData = resolveIcon(slideData.icon, assets);
  addDarkSlideHeading(slide, slideData.heading, iconData);

  // Numbered takeaway items
  const items = slideData.items || [];
  let yPos = 2.3;
  for (let i = 0; i < Math.min(items.length, 5); i++) {
    const t = items[i];
    const num = String(i + 1).padStart(2, "0");

    // Number badge
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: yPos + 0.05, w: 0.55, h: 0.55,
      fill: { color: GOLD },
    });
    slide.addText(num, {
      x: 0.7, y: yPos + 0.05, w: 0.55, h: 0.55,
      fontFace: BODY_FONT, fontSize: 13, color: NAVY,
      bold: true, align: "center", valign: "middle", margin: 0,
    });
    // Title
    slide.addText(t.title, {
      x: 1.5, y: yPos, w: 7.8, h: 0.5,
      fontFace: HEADER_FONT, fontSize: 18, color: GOLD,
      bold: true, margin: 0,
    });
    // Body
    slide.addText(t.body, {
      x: 1.5, y: yPos + 0.55, w: 7.8, h: 0.65,
      fontFace: BODY_FONT, fontSize: 15, color: MUTED,
      margin: 0, lineSpacingMultiple: 1.2,
    });
    yPos += 1.55;
  }

  // Signal line decoration
  slide.addImage({ data: assets.signalLine, x: 0.5, y: 8.6, w: 9, h: 0.5, transparency: 60 });

  addFooter(pres, slide, pageNum, true);
}

function buildTimelineSlide(pres, slideData, assets, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  addHeader(pres, slide);

  const iconData = resolveIcon(slideData.icon, assets);
  addSlideHeading(slide, slideData.heading, iconData);

  const items = slideData.items || [];
  const startY = 2.6;
  const spacing = Math.min(1.3, 5.5 / Math.max(items.length, 1));

  // Vertical timeline line
  const lineEndY = startY + (items.length - 1) * spacing + 0.15;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 1.38, y: startY, w: 0.04, h: lineEndY - startY,
    fill: { color: GOLD },
  });

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const y = startY + i * spacing;

    // Gold dot
    slide.addShape(pres.shapes.OVAL, {
      x: 1.2, y: y, w: 0.4, h: 0.4,
      fill: { color: GOLD },
    });

    // Date label
    slide.addText(item.date, {
      x: 1.9, y: y - 0.05, w: 2.5, h: 0.4,
      fontFace: BODY_FONT, fontSize: 13, color: GOLD,
      bold: true, margin: 0,
    });

    // Event description
    slide.addText(item.event, {
      x: 1.9, y: y + 0.35, w: 7.0, h: 0.6,
      fontFace: BODY_FONT, fontSize: 16, color: BODY_TEXT,
      margin: 0, lineSpacingMultiple: 1.2,
    });
  }

  addFooter(pres, slide, pageNum);
}

function buildScenariosSlide(pres, slideData, assets, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  addHeader(pres, slide);

  const iconData = resolveIcon(slideData.icon, assets);
  addSlideHeading(slide, slideData.heading, iconData);

  const scenarios = [
    { data: slideData.bull, color: "27AE60", x: 0.5 },   // green
    { data: slideData.base, color: GOLD,     x: 3.5 },   // gold
    { data: slideData.bear, color: "C0392B", x: 6.5 },   // red
  ];

  for (const s of scenarios) {
    if (!s.data) continue;

    // Card
    slide.addShape(pres.shapes.RECTANGLE, {
      x: s.x, y: 2.5, w: 2.8, h: 5.5,
      fill: { color: WHITE },
      shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.06 },
    });
    // Color top bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: s.x, y: 2.5, w: 2.8, h: 0.06,
      fill: { color: s.color },
    });
    // Label
    slide.addText(s.data.label, {
      x: s.x, y: 2.8, w: 2.8, h: 0.5,
      fontFace: BODY_FONT, fontSize: 11, color: s.color,
      bold: true, charSpacing: 3, align: "center", margin: 0,
    });
    // Value (big number)
    slide.addText(s.data.value, {
      x: s.x, y: 3.6, w: 2.8, h: 1.5,
      fontFace: HEADER_FONT, fontSize: 44, color: s.color,
      bold: true, align: "center", valign: "middle", margin: 0,
    });
    // Detail
    slide.addText(s.data.detail, {
      x: s.x + 0.3, y: 5.5, w: 2.2, h: 2.0,
      fontFace: BODY_FONT, fontSize: 14, color: MUTED,
      align: "center", valign: "top", margin: 0,
      lineSpacingMultiple: 1.3,
    });
  }

  addFooter(pres, slide, pageNum);
}

function buildSingleStatSlide(pres, slideData, assets, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: NAVY };

  // Grid overlay
  slide.addImage({ data: assets.gridPattern, x: 0, y: 0, w: 10, h: 10, transparency: 85 });

  // Dark header
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: DEEP_BLUE },
  });
  slide.addText("STERLING SIGNALS", {
    x: 0.6, y: 0.1, w: 4, h: 0.55,
    fontFace: BODY_FONT, fontSize: 14, color: GOLD,
    bold: true, charSpacing: 5, valign: "middle", margin: 0,
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.75, w: 10, h: 0.04,
    fill: { color: GOLD },
  });

  // Big number centered
  slide.addText(slideData.number, {
    x: 0.5, y: 2.5, w: 9, h: 2.5,
    fontFace: HEADER_FONT, fontSize: 96, color: GOLD,
    bold: true, align: "center", valign: "middle", margin: 0,
  });

  // Label
  slide.addText(slideData.label, {
    x: 1.5, y: 5.2, w: 7, h: 0.8,
    fontFace: BODY_FONT, fontSize: 24, color: WHITE,
    align: "center", valign: "middle", margin: 0,
  });

  // Sublabel
  if (slideData.sublabel) {
    slide.addText(slideData.sublabel, {
      x: 1.5, y: 6.2, w: 7, h: 0.8,
      fontFace: BODY_FONT, fontSize: 16, color: MUTED,
      align: "center", valign: "middle", margin: 0,
    });
  }

  // Signal line decoration
  slide.addImage({ data: assets.signalLine, x: 0.5, y: 8.2, w: 9, h: 0.5, transparency: 60 });

  addFooter(pres, slide, pageNum, true);
}

// ---------------------------------------------------------------------------
// Slide type dispatcher
// ---------------------------------------------------------------------------
const SLIDE_BUILDERS = {
  context: buildContextSlide,
  stats: buildStatsSlide,
  two_column: buildTwoColumnSlide,
  takeaway: buildTakeawaySlide,
  timeline: buildTimelineSlide,
  scenarios: buildScenariosSlide,
  single_stat: buildSingleStatSlide,
};

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  // --- Read JSON data ---
  const jsonPath = process.argv[2];
  if (!jsonPath) {
    console.error("Usage: node carousel-generator.js <path-to-data.json>");
    process.exit(1);
  }

  let data;
  try {
    const raw = fs.readFileSync(jsonPath, "utf-8");
    data = JSON.parse(raw);
  } catch (err) {
    console.error(`Error reading ${jsonPath}: ${err.message}`);
    process.exit(1);
  }

  // Validate required fields
  if (!data.title || !data.slides || !Array.isArray(data.slides)) {
    console.error("JSON must have 'title' and 'slides' array.");
    process.exit(1);
  }

  // --- Create presentation ---
  const pres = new pptxgen();
  pres.defineLayout({ name: "SQUARE", width: 10, height: 10 });
  pres.layout = "SQUARE";
  pres.author = "Sterling Signals";
  pres.title = data.title.replace(/\n/g, " ");

  // --- Pre-generate assets ---
  console.log("Generating assets...");
  const gridPattern = await generateGridPattern(`#${STEEL}`, 0.08);
  const signalLine = await generateSignalLine(`#${GOLD}`, 1200, 120);
  const signalLineWhite = await generateSignalLine(`#${WHITE}`, 1200, 120);

  // Pre-generate all referenced icons
  const icons = {};
  const usedIcons = new Set();
  usedIcons.add("chart_line"); // always needed for title slide
  for (const slide of data.slides) {
    if (slide.icon) usedIcons.add(slide.icon);
  }
  for (const iconName of usedIcons) {
    const IconComponent = ICON_MAP[iconName];
    if (IconComponent) {
      // Gold icons for light slides, white for chart_line on title
      icons[iconName] = await iconToBase64Png(
        IconComponent,
        `#${iconName === "chart_line" ? WHITE : GOLD}`,
        256
      );
    }
  }

  const assets = {
    gridPattern,
    signalLine,
    signalLineWhite,
    chartLineIcon: icons.chart_line,
    icons,
  };

  // --- Build slides ---
  console.log("Building title slide...");
  buildTitleSlide(pres, data, assets);

  let pageNum = 2; // title is page 1
  for (const slideData of data.slides) {
    const builder = SLIDE_BUILDERS[slideData.type];
    if (!builder) {
      console.warn(`Unknown slide type: "${slideData.type}" — skipping`);
      continue;
    }
    console.log(`Building ${slideData.type} slide (page ${pageNum})...`);
    builder(pres, slideData, assets, pageNum);
    pageNum++;
  }

  // --- Resolve output path ---
  const scriptDir = __dirname;
  const projectRoot = path.resolve(scriptDir, "..", "..");
  const defaultOutputDir = path.join(projectRoot, "substack", "output", "current", "carousels");

  const outputDir = data.output_path
    ? path.resolve(data.output_path)
    : defaultOutputDir;

  const filename = data.output_filename || "sterling-signals-carousel.pptx";
  const outputPath = path.join(outputDir, filename);

  // Ensure output directory exists
  fs.mkdirSync(outputDir, { recursive: true });

  // --- Write file ---
  await pres.writeFile({ fileName: outputPath });
  console.log(`Done: ${outputPath}`);
  console.log(`Slides: ${pageNum - 1} (1 title + ${data.slides.length} content)`);
}

main().catch((err) => {
  console.error("Fatal error:", err.message);
  process.exit(1);
});
