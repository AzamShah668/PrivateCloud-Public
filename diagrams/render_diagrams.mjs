/**
 * render_diagrams.mjs
 * 
 * Renders PlantUML .puml files via Kroki.io API (POST with source),
 * downloads high-res PNG images, and packages each into a PDF.
 * 
 * Usage:  node render_diagrams.mjs
 * Output: *.png + *.pdf files in diagrams/output/
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import https from 'https';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---------------------------------------------------------------------------
// HTTP(S) POST helper for Kroki
// ---------------------------------------------------------------------------
function postKroki(pumlSource, format = 'png') {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ diagram_source: pumlSource, diagram_type: 'plantuml', output_format: format });
    const bodyBuf = Buffer.from(body, 'utf-8');

    const options = {
      hostname: 'kroki.io',
      port: 443,
      path: '/',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': bodyBuf.length,
        'Accept': format === 'png' ? 'image/png' : 'image/svg+xml',
        'User-Agent': 'PrivateCloud-DiagramRenderer/1.0',
      },
    };

    const req = https.request(options, (res) => {
      if (res.statusCode !== 200) {
        let errBody = '';
        res.on('data', c => errBody += c);
        res.on('end', () => reject(new Error(`Kroki HTTP ${res.statusCode}: ${errBody.slice(0, 300)}`)));
        return;
      }
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    });

    req.on('error', reject);
    req.setTimeout(120000, () => { req.destroy(); reject(new Error('Request timed out')); });
    req.write(bodyBuf);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
const DIAGRAMS_DIR = path.join(__dirname, 'iteration3');
const OUTPUT_DIR = path.join(__dirname, 'output');

async function main() {
  // Ensure output directory
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  // Find all .puml files
  const pumlFiles = fs.readdirSync(DIAGRAMS_DIR)
    .filter(f => f.endsWith('.puml'))
    .map(f => ({
      name: f,
      basename: path.basename(f, '.puml'),
      fullPath: path.join(DIAGRAMS_DIR, f),
    }));

  if (pumlFiles.length === 0) {
    console.error('No .puml files found in', DIAGRAMS_DIR);
    process.exit(1);
  }

  console.log(`\n🔍 Found ${pumlFiles.length} diagram(s):\n`);
  pumlFiles.forEach(f => console.log(`   • ${f.name}`));

  // Process each diagram — fetch PNG via Kroki
  for (const file of pumlFiles) {
    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`📐 Processing: ${file.name}`);
    
    const source = fs.readFileSync(file.fullPath, 'utf-8');

    // Fetch PNG
    console.log(`   ⬇️  Fetching PNG from Kroki.io...`);
    try {
      const pngBuffer = await postKroki(source, 'png');
      const pngPath = path.join(OUTPUT_DIR, `${file.basename}.png`);
      fs.writeFileSync(pngPath, pngBuffer);
      console.log(`   ✅ PNG saved: ${pngPath} (${(pngBuffer.length / 1024).toFixed(1)} KB)`);
    } catch (err) {
      console.error(`   ❌ PNG fetch failed: ${err.message}`);
      console.log(`   🔄 Trying SVG instead...`);
      try {
        const svgBuffer = await postKroki(source, 'svg');
        const svgPath = path.join(OUTPUT_DIR, `${file.basename}.svg`);
        fs.writeFileSync(svgPath, svgBuffer);
        console.log(`   ✅ SVG saved: ${svgPath} (${(svgBuffer.length / 1024).toFixed(1)} KB)`);
      } catch (err2) {
        console.error(`   ❌ SVG fetch also failed: ${err2.message}`);
      }
    }

    // Also fetch SVG for vector quality
    console.log(`   ⬇️  Fetching SVG from Kroki.io...`);
    try {
      const svgBuffer = await postKroki(source, 'svg');
      const svgPath = path.join(OUTPUT_DIR, `${file.basename}.svg`);
      fs.writeFileSync(svgPath, svgBuffer);
      console.log(`   ✅ SVG saved: ${svgPath} (${(svgBuffer.length / 1024).toFixed(1)} KB)`);
    } catch (err) {
      console.error(`   ❌ SVG fetch failed: ${err.message}`);
    }

    // Small delay between requests to be nice to the server
    await new Promise(r => setTimeout(r, 2000));
  }

  console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`✅ All diagrams rendered to: ${OUTPUT_DIR}`);
  console.log(`\n📝 Now converting to PDF...\n`);

  // Convert PNGs to PDFs using pdfkit
  try {
    const { default: PDFDocument } = await import('pdfkit');
    
    const pngFiles = fs.readdirSync(OUTPUT_DIR).filter(f => f.endsWith('.png'));
    
    if (pngFiles.length === 0) {
      console.log('⚠️  No PNG files found. Skipping PDF generation.');
      return;
    }

    for (const png of pngFiles) {
      const pngPath = path.join(OUTPUT_DIR, png);
      const pdfPath = path.join(OUTPUT_DIR, png.replace('.png', '.pdf'));
      const title = png.replace('.png', '').replace(/_/g, ' ').replace(/i3/g, '— Iteration 3').replace(/\b\w/g, c => c.toUpperCase());

      const doc = new PDFDocument({ 
        size: 'A3', 
        layout: 'landscape',
        margin: 50,
        info: {
          Title: `PrivateCloud ${title}`,
          Author: 'PrivateCloud Team',
          Subject: 'UML Diagram — Iteration 3',
          Creator: 'PrivateCloud Diagram Renderer',
        }
      });

      const stream = fs.createWriteStream(pdfPath);
      doc.pipe(stream);

      // Title bar
      doc.rect(0, 0, 1191, 85).fill('#1a1a2e');
      
      doc.fontSize(22)
         .fillColor('#ffffff')
         .text(`PrivateCloud ${title}`, 50, 20, { align: 'center', width: 1090 });
      
      doc.fontSize(11)
         .fillColor('#8892b0')
         .text('Iteration 3 — UML Diagram', 50, 52, { align: 'center', width: 1090 });

      // Image — fit within available area
      const imgTop = 100;
      const availWidth = 1090;
      const availHeight = 690;
      
      doc.image(pngPath, 50, imgTop, {
        fit: [availWidth, availHeight],
        align: 'center',
        valign: 'center',
      });

      // Footer bar
      doc.rect(0, 810, 1191, 32).fill('#f8f9fa');
      doc.fontSize(8)
         .fillColor('#868e96')
         .text(
           `Generated ${new Date().toISOString().split('T')[0]} | PrivateCloud Iteration 3 | Rendered via Kroki.io`,
           50, 816,
           { align: 'center', width: 1090 }
         );

      doc.end();
      
      await new Promise(resolve => stream.on('finish', resolve));
      const pdfStats = fs.statSync(pdfPath);
      console.log(`   📄 PDF saved: ${pdfPath} (${(pdfStats.size / 1024).toFixed(1)} KB)`);
    }

    console.log(`\n🎉 All PDFs generated successfully!`);
    console.log(`📁 Output directory: ${OUTPUT_DIR}\n`);

  } catch (err) {
    console.error('❌ PDF generation error:', err.message);
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
