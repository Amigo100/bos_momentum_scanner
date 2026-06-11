const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaBolt, FaChartBar, FaShieldAlt, FaLightbulb, FaChartLine } = require("react-icons/fa");

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

// Generate a subtle geometric pattern for backgrounds
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

// Generate a signal/pulse line SVG
async function generateSignalLine(color, width = 1200, height = 120) {
  const mid = height / 2;
  const points = [];
  // Flat start, then a sharp signal pulse, then flat end
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
    <polyline points="${points.join(' ')}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

async function main() {
  let pres = new pptxgen();
  pres.defineLayout({ name: "SQUARE", width: 10, height: 10 });
  pres.layout = "SQUARE";
  pres.author = "Sterling Signals";
  pres.title = "AI Is Eating Software Stocks";

  // === STERLING SIGNALS PALETTE ===
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

  // Pre-generate assets
  const boltIcon = await iconToBase64Png(FaBolt, `#${GOLD}`, 256);
  const chartBarIcon = await iconToBase64Png(FaChartBar, `#${GOLD}`, 256);
  const shieldIcon = await iconToBase64Png(FaShieldAlt, `#${GOLD}`, 256);
  const lightbulbIcon = await iconToBase64Png(FaLightbulb, `#${GOLD}`, 256);
  const chartLineIcon = await iconToBase64Png(FaChartLine, `#${WHITE}`, 256);
  const gridPattern = await generateGridPattern(`#${STEEL}`, 0.08);
  const signalLine = await generateSignalLine(`#${GOLD}`, 1200, 120);
  const signalLineWhite = await generateSignalLine(`#${WHITE}`, 1200, 120);

  // === HELPER: Add branded header bar ===
  function addHeader(slide, isDark = false) {
    // Top bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 0.75,
      fill: { color: isDark ? NAVY : NAVY }
    });
    // Brand name
    slide.addText("STERLING SIGNALS", {
      x: 0.6, y: 0.1, w: 4, h: 0.55,
      fontFace: BODY_FONT, fontSize: 14, color: WHITE,
      bold: true, charSpacing: 5, valign: "middle", margin: 0
    });
    // Gold accent line beneath bar
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0.75, w: 10, h: 0.04,
      fill: { color: GOLD }
    });
  }

  // === HELPER: Add branded footer ===
  function addFooter(slide, pageNum, isDark = false) {
    const footY = 9.2;
    // Divider line
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: footY, w: 8.8, h: 0.01,
      fill: { color: isDark ? STEEL : ICE }
    });
    // Left: brand
    slide.addText("sterlingsignals.co", {
      x: 0.6, y: footY + 0.15, w: 4, h: 0.4,
      fontFace: BODY_FONT, fontSize: 10, color: isDark ? STEEL : MUTED,
      margin: 0
    });
    // Right: page number
    slide.addText(String(pageNum).padStart(2, "0"), {
      x: 7.8, y: footY + 0.15, w: 1.6, h: 0.4,
      fontFace: BODY_FONT, fontSize: 11, color: isDark ? STEEL : MUTED,
      align: "right", margin: 0
    });
  }

  // ============================
  // SLIDE 1: TITLE (Dark)
  // ============================
  let s1 = pres.addSlide();
  s1.background = { color: NAVY };

  // Subtle grid overlay
  s1.addImage({ data: gridPattern, x: 0, y: 0, w: 10, h: 10, transparency: 80 });

  // Header bar (slightly lighter to distinguish)
  s1.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: DEEP_BLUE }
  });
  s1.addText("STERLING SIGNALS", {
    x: 0.6, y: 0.1, w: 4, h: 0.55,
    fontFace: BODY_FONT, fontSize: 14, color: GOLD,
    bold: true, charSpacing: 5, valign: "middle", margin: 0
  });
  // Signal line icon next to brand
  s1.addImage({ data: chartLineIcon, x: 5.4, y: 0.15, w: 0.4, h: 0.4 });
  s1.addText("MACRO PULSE", {
    x: 5.85, y: 0.1, w: 3, h: 0.55,
    fontFace: BODY_FONT, fontSize: 11, color: MUTED,
    charSpacing: 3, valign: "middle", margin: 0
  });

  // Gold accent line
  s1.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.75, w: 10, h: 0.04,
    fill: { color: GOLD }
  });

  // Signal pulse decoration
  s1.addImage({ data: signalLineWhite, x: 0.5, y: 2.2, w: 9, h: 0.9, transparency: 85 });

  // Main title
  s1.addText([
    { text: "AI IS EATING", options: { breakLine: true, color: WHITE } },
    { text: "SOFTWARE STOCKS", options: { color: GOLD } }
  ], {
    x: 0.8, y: 3.0, w: 8.4, h: 3.0,
    fontFace: HEADER_FONT, fontSize: 60, bold: true,
    align: "center", valign: "middle",
    lineSpacingMultiple: 1.1, margin: 0
  });

  // Subtitle
  s1.addText("What the $285B selloff means for investors", {
    x: 1.5, y: 6.2, w: 7, h: 0.6,
    fontFace: BODY_FONT, fontSize: 18, color: MUTED,
    align: "center", margin: 0
  });

  // Date tag
  s1.addText("MARCH 2026", {
    x: 3.5, y: 7.2, w: 3, h: 0.4,
    fontFace: BODY_FONT, fontSize: 12, color: STEEL,
    align: "center", charSpacing: 3, margin: 0
  });

  // Swipe indicator
  s1.addShape(pres.shapes.RECTANGLE, {
    x: 3.8, y: 8.4, w: 2.4, h: 0.45,
    fill: { color: DEEP_BLUE },
    line: { color: STEEL, width: 0.8 }
  });
  s1.addText("SWIPE \u2192", {
    x: 3.8, y: 8.4, w: 2.4, h: 0.45,
    fontFace: BODY_FONT, fontSize: 10, color: MUTED,
    charSpacing: 3, align: "center", valign: "middle", margin: 0
  });

  addFooter(s1, 1, true);

  // ============================
  // SLIDE 2: What Happened (Light)
  // ============================
  let s2 = pres.addSlide();
  s2.background = { color: LIGHT_BG };
  addHeader(s2);

  s2.addImage({ data: boltIcon, x: 0.7, y: 1.2, w: 0.5, h: 0.5 });
  s2.addText("What Happened", {
    x: 1.4, y: 1.15, w: 6, h: 0.6,
    fontFace: HEADER_FONT, fontSize: 30, color: DARK_TEXT,
    bold: true, margin: 0
  });

  // Gold accent bar
  s2.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.95, w: 2.5, h: 0.04,
    fill: { color: GOLD }
  });

  s2.addText([
    { text: "Anthropic launched Cowork in January 2026 \u2014 a desktop AI agent that organizes files, analyzes data, generates reports, and automates multi-step workflows.", options: { breakLine: true, paraSpaceAfter: 16 } },
    { text: "Within days, investors repriced every SaaS company whose product overlaps with what an AI agent can now do for $20/month.", options: { breakLine: true, paraSpaceAfter: 16 } },
    { text: "The result: $285 billion wiped from software stocks in a single wave.", options: { bold: true, color: DARK_TEXT } }
  ], {
    x: 0.7, y: 2.4, w: 8.6, h: 4.0,
    fontFace: BODY_FONT, fontSize: 19, color: BODY_TEXT,
    lineSpacingMultiple: 1.4, margin: 0
  });

  // Callout box
  s2.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 7.0, w: 8.6, h: 1.5,
    fill: { color: WHITE }
  });
  s2.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 7.0, w: 0.06, h: 1.5,
    fill: { color: GOLD }
  });
  s2.addText("This isn\u2019t about one product. It\u2019s a repricing of the entire category of \u2018workflow automation\u2019 software.", {
    x: 1.15, y: 7.0, w: 7.8, h: 1.5,
    fontFace: HEADER_FONT, fontSize: 16, color: STEEL,
    italic: true, valign: "middle", margin: 0
  });

  addFooter(s2, 2);

  // ============================
  // SLIDE 3: The Numbers (Light)
  // ============================
  let s3 = pres.addSlide();
  s3.background = { color: LIGHT_BG };
  addHeader(s3);

  s3.addImage({ data: chartBarIcon, x: 0.7, y: 1.2, w: 0.5, h: 0.5 });
  s3.addText("The Numbers", {
    x: 1.4, y: 1.15, w: 6, h: 0.6,
    fontFace: HEADER_FONT, fontSize: 30, color: DARK_TEXT,
    bold: true, margin: 0
  });
  s3.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.95, w: 2.5, h: 0.04,
    fill: { color: GOLD }
  });

  const stats = [
    { number: "$285B", label: "wiped from software\nstocks in days", x: 0.7, y: 2.4 },
    { number: "25\u201360%", label: "drawdowns in some\nSaaS names", x: 5.2, y: 2.4 },
    { number: "$20/mo", label: "cost of Claude Pro \u2014\nreplacing $500/seat tools", x: 0.7, y: 5.5 },
    { number: "80%", label: "of Anthropic revenue\nnow from enterprise", x: 5.2, y: 5.5 },
  ];

  for (const stat of stats) {
    // Card
    s3.addShape(pres.shapes.RECTANGLE, {
      x: stat.x, y: stat.y, w: 4.1, h: 2.6,
      fill: { color: WHITE },
      shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.06 }
    });
    // Gold top accent
    s3.addShape(pres.shapes.RECTANGLE, {
      x: stat.x, y: stat.y, w: 4.1, h: 0.05,
      fill: { color: GOLD }
    });
    // Number
    s3.addText(stat.number, {
      x: stat.x + 0.45, y: stat.y + 0.35, w: 3.2, h: 1.0,
      fontFace: HEADER_FONT, fontSize: 40, color: MID_BLUE,
      bold: true, margin: 0
    });
    // Label
    s3.addText(stat.label, {
      x: stat.x + 0.45, y: stat.y + 1.35, w: 3.2, h: 1.0,
      fontFace: BODY_FONT, fontSize: 15, color: MUTED,
      margin: 0, lineSpacingMultiple: 1.25
    });
  }

  addFooter(s3, 3);

  // ============================
  // SLIDE 4: Who's Vulnerable (Light)
  // ============================
  let s4 = pres.addSlide();
  s4.background = { color: LIGHT_BG };
  addHeader(s4);

  s4.addImage({ data: shieldIcon, x: 0.7, y: 1.2, w: 0.5, h: 0.5 });
  s4.addText("Who\u2019s Vulnerable", {
    x: 1.4, y: 1.15, w: 6, h: 0.6,
    fontFace: HEADER_FONT, fontSize: 30, color: DARK_TEXT,
    bold: true, margin: 0
  });
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.95, w: 2.5, h: 0.04,
    fill: { color: GOLD }
  });

  // AT RISK column - card with red-ish tint
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 2.4, w: 4.1, h: 6.2,
    fill: { color: WHITE },
    shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.06 }
  });
  // Red top bar
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 2.4, w: 4.1, h: 0.05,
    fill: { color: "C0392B" }
  });
  s4.addText("AT RISK", {
    x: 0.7, y: 2.7, w: 4.1, h: 0.45,
    fontFace: BODY_FONT, fontSize: 12, color: "C0392B",
    bold: true, charSpacing: 4, align: "center", margin: 0
  });

  const atRisk = [
    "Task automation platforms",
    "Basic CRM tools",
    "Simple reporting software",
    "File management tools",
    "Low-code workflow builders",
    "Generic writing assistants"
  ];
  s4.addText(atRisk.map((item, i) => ({
    text: item,
    options: { bullet: true, breakLine: i < atRisk.length - 1, paraSpaceAfter: 12, color: BODY_TEXT }
  })), {
    x: 1.2, y: 3.4, w: 3.2, h: 4.8, valign: "top",
    fontFace: BODY_FONT, fontSize: 15, lineSpacingMultiple: 1.35, margin: 0
  });

  // DEFENSIBLE column
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 2.4, w: 4.1, h: 6.2,
    fill: { color: WHITE },
    shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.06 }
  });
  // Green top bar
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 2.4, w: 4.1, h: 0.05,
    fill: { color: "27AE60" }
  });
  s4.addText("DEFENSIBLE", {
    x: 5.2, y: 2.7, w: 4.1, h: 0.45,
    fontFace: BODY_FONT, fontSize: 12, color: "27AE60",
    bold: true, charSpacing: 4, align: "center", margin: 0
  });

  const defensible = [
    "Deep data network effects",
    "Regulated compliance tools",
    "Proprietary datasets (S&P, FactSet)",
    "Mission-critical infrastructure",
    "High switching-cost platforms",
    "Vertical-specific solutions"
  ];
  s4.addText(defensible.map((item, i) => ({
    text: item,
    options: { bullet: true, breakLine: i < defensible.length - 1, paraSpaceAfter: 12, color: BODY_TEXT }
  })), {
    x: 5.7, y: 3.4, w: 3.2, h: 4.8, valign: "top",
    fontFace: BODY_FONT, fontSize: 15, lineSpacingMultiple: 1.35, margin: 0
  });

  addFooter(s4, 4);

  // ============================
  // SLIDE 5: Takeaway (Dark)
  // ============================
  let s5 = pres.addSlide();
  s5.background = { color: NAVY };
  s5.addImage({ data: gridPattern, x: 0, y: 0, w: 10, h: 10, transparency: 85 });

  // Header on dark
  s5.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.75,
    fill: { color: DEEP_BLUE }
  });
  s5.addText("STERLING SIGNALS", {
    x: 0.6, y: 0.1, w: 4, h: 0.55,
    fontFace: BODY_FONT, fontSize: 14, color: GOLD,
    bold: true, charSpacing: 5, valign: "middle", margin: 0
  });
  s5.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.75, w: 10, h: 0.04,
    fill: { color: GOLD }
  });

  s5.addImage({ data: lightbulbIcon, x: 0.7, y: 1.2, w: 0.5, h: 0.5 });
  s5.addText("The Takeaway", {
    x: 1.4, y: 1.15, w: 6, h: 0.6,
    fontFace: HEADER_FONT, fontSize: 30, color: WHITE,
    bold: true, margin: 0
  });
  s5.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.95, w: 2.5, h: 0.04,
    fill: { color: GOLD }
  });

  const takeaways = [
    {
      num: "01",
      title: "This is structural, not cyclical.",
      body: "AI agents won\u2019t get worse. The companies they threaten need to adapt or be repriced permanently."
    },
    {
      num: "02",
      title: "Don\u2019t catch the falling knife.",
      body: "A stock down 40% isn\u2019t cheap if AI eliminates the core value proposition entirely."
    },
    {
      num: "03",
      title: "Follow the moat.",
      body: "Proprietary data, regulatory barriers, and network effects still matter. Commodity workflow tools are the targets."
    },
    {
      num: "04",
      title: "The AI builders are the new infrastructure.",
      body: "Anthropic, OpenAI, and their cloud partners are building the picks and shovels of this cycle."
    }
  ];

  let yPos = 2.3;
  for (const t of takeaways) {
    // Number badge
    s5.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: yPos + 0.05, w: 0.55, h: 0.55,
      fill: { color: GOLD }
    });
    s5.addText(t.num, {
      x: 0.7, y: yPos + 0.05, w: 0.55, h: 0.55,
      fontFace: BODY_FONT, fontSize: 13, color: NAVY,
      bold: true, align: "center", valign: "middle", margin: 0
    });
    // Title
    s5.addText(t.title, {
      x: 1.5, y: yPos, w: 7.8, h: 0.5,
      fontFace: HEADER_FONT, fontSize: 18, color: GOLD,
      bold: true, margin: 0
    });
    // Body
    s5.addText(t.body, {
      x: 1.5, y: yPos + 0.55, w: 7.8, h: 0.65,
      fontFace: BODY_FONT, fontSize: 15, color: MUTED,
      margin: 0, lineSpacingMultiple: 1.2
    });
    yPos += 1.55;
  }

  // Signal line decoration at bottom
  s5.addImage({ data: signalLine, x: 0.5, y: 8.6, w: 9, h: 0.5, transparency: 60 });

  addFooter(s5, 5, true);

  await pres.writeFile({ fileName: "/home/claude/sterling-signals-carousel.pptx" });
  console.log("Done: sterling-signals-carousel.pptx");
}

main().catch(console.error);
