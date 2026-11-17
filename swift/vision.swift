#!/usr/bin/env swift

import Foundation
import AppKit
import Vision
import PDFKit

// ─────────────────────────────────────────────
// MARK: - Configuration
// ─────────────────────────────────────────────

struct Config {
    var paths:         [String]                          = []
    var languages:     [String]                          = ["fr-FR", "en-US"]
    var level:         VNRequestTextRecognitionLevel     = .accurate
    var outputFile:    String?                           = nil
    var minConfidence: Float                             = 0.0
    var jsonOutput:    Bool                              = false
    var noCorrection:  Bool                              = false
    var alsoStdout:    Bool                              = false  // --stdout : stdout + fichier simultanément
    var maxPages:      Int?                              = nil    // --pages N : limite le nombre de pages PDF
}

// ─────────────────────────────────────────────
// MARK: - Résultat OCR
// ─────────────────────────────────────────────

struct OCRLine: Encodable {
    let text:       String
    let confidence: Float
}

struct OCRPage: Encodable {
    let source: String
    let page:   Int         // 1 pour les images
    let lines:  [OCRLine]

    var plainText: String {
        lines.map(\.text).joined(separator: "\n")
    }
}

// ─────────────────────────────────────────────
// MARK: - Parsing des arguments
// ─────────────────────────────────────────────

func printUsage() {
    print("""
    Usage: swiftocr [options] <fichier1> [fichier2 ...] [--dir <dossier>]

    Arguments :
      <fichier>           Image (jpg, png, tiff…) ou PDF
      --dir <dossier>     Traite tous les fichiers supportés dans le dossier

    Options :
      --lang <codes>      Langues séparées par virgule  (défaut : fr-FR,en-US)
      --level <n>         Niveau OCR : fast | accurate  (défaut : accurate)
      --output <fichier>  Écrit le résultat dans un fichier texte ou JSON
      --min-conf <n>      Score de confiance minimum 0.0–1.0  (défaut : 0.0)
      --json              Sortie au format JSON structuré
      --no-correction     Désactive la correction linguistique
      --stdout            Écrit aussi sur stdout quand --output est utilisé
      --pages <n>         Limite le traitement aux N premières pages (PDF uniquement)
      --help              Affiche cette aide
    """)
}

func parseArgs(_ args: [String]) -> Config {
    var config = Config()
    var i = 1  // ignorer argv[0]

    while i < args.count {
        switch args[i] {

        case "--help":
            printUsage(); exit(0)

        case "--lang":
            i += 1
            guard i < args.count else { fatal("--lang attend une valeur.") }
            config.languages = args[i].split(separator: ",").map(String.init)

        case "--level":
            i += 1
            guard i < args.count else { fatal("--level attend fast|accurate.") }
            switch args[i] {
            case "fast":     config.level = .fast
            case "accurate": config.level = .accurate
            default:         fatal("--level : valeur invalide '\(args[i])'. Utilisez fast ou accurate.")
            }

        case "--output":
            i += 1
            guard i < args.count else { fatal("--output attend un chemin de fichier.") }
            config.outputFile = args[i]

        case "--min-conf":
            i += 1
            guard i < args.count, let v = Float(args[i]) else { fatal("--min-conf attend un nombre entre 0.0 et 1.0.") }
            config.minConfidence = v

        case "--json":
            config.jsonOutput = true

        case "--no-correction":
            config.noCorrection = true

        case "--stdout":
            config.alsoStdout = true

        case "--pages":
            i += 1
            guard i < args.count, let n = Int(args[i]), n > 0 else {
                fatal("--pages attend un entier positif.")
            }
            config.maxPages = n

        case "--dir":
            i += 1
            guard i < args.count else { fatal("--dir attend un chemin de dossier.") }
            let dir = args[i]
            guard let entries = try? FileManager.default.contentsOfDirectory(atPath: dir) else {
                fatal("Impossible de lire le dossier '\(dir)'.")
            }
            let supported = ["jpg","jpeg","png","tiff","tif","bmp","heic","pdf"]
            let found = entries
                .filter { supported.contains(($0 as NSString).pathExtension.lowercased()) }
                .map    { "\(dir)/\($0)" }
                .sorted()
            guard !found.isEmpty else { fatal("Aucun fichier supporté dans '\(dir)'.") }
            config.paths.append(contentsOf: found)

        default:
            // Tout argument ne commençant pas par "--" est un chemin de fichier
            if args[i].hasPrefix("--") {
                fatal("Option inconnue : '\(args[i])'. Utilisez --help.")
            }
            config.paths.append(args[i])
        }
        i += 1
    }

    if config.paths.isEmpty {
        printUsage(); exit(1)
    }
    return config
}

// ─────────────────────────────────────────────
// MARK: - Helpers
// ─────────────────────────────────────────────

func fatal(_ msg: String) -> Never {
    fputs("Erreur : \(msg)\n", stderr); exit(1)
}

/// Exécute la requête Vision sur un CGImage et retourne les lignes filtrées.
func runOCR(on cgImage: CGImage, config: Config) -> [OCRLine] {
    let semaphore = DispatchSemaphore(value: 0)
    var lines: [OCRLine] = []

    let request = VNRecognizeTextRequest { req, err in
        defer { semaphore.signal() }
        if let err = err { fatal("Vision : \(err.localizedDescription)") }

        guard let obs = req.results as? [VNRecognizedTextObservation] else { return }

        // Tri spatial : haut → bas, puis gauche → droite
        let sorted = obs.sorted {
            let dy = $1.boundingBox.midY - $0.boundingBox.midY
            return abs(dy) > 0.01 ? dy < 0 : $0.boundingBox.midX < $1.boundingBox.midX
        }

        lines = sorted.compactMap { obs -> OCRLine? in
            guard let best = obs.topCandidates(1).first,
                  best.confidence >= config.minConfidence else { return nil }
            return OCRLine(text: best.string, confidence: best.confidence)
        }
    }

    request.recognitionLevel      = config.level
    request.usesLanguageCorrection = !config.noCorrection
    request.recognitionLanguages  = config.languages

    let handler = VNImageRequestHandler(cgImage: cgImage, orientation: .up, options: [:])
    do {
        try handler.perform([request])
    } catch {
        fatal("Impossible d'exécuter Vision : \(error.localizedDescription)")
    }

    semaphore.wait()
    return lines
}

// ─────────────────────────────────────────────
// MARK: - Traitement fichier image
// ─────────────────────────────────────────────

func processImage(path: String, config: Config) -> [OCRPage] {
    guard let image = NSImage(contentsOfFile: path) else {
        fputs("Avertissement : impossible de charger '\(path)', ignoré.\n", stderr)
        return []
    }
    guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        fputs("Avertissement : impossible de convertir '\(path)' en CGImage, ignoré.\n", stderr)
        return []
    }
    let lines = runOCR(on: cg, config: config)
    return [OCRPage(source: path, page: 1, lines: lines)]
}

// ─────────────────────────────────────────────
// MARK: - Traitement PDF multi-pages
// ─────────────────────────────────────────────

func processPDF(path: String, config: Config) -> [OCRPage] {
    guard let pdf = PDFDocument(url: URL(fileURLWithPath: path)) else {
        fputs("Avertissement : impossible d'ouvrir le PDF '\(path)', ignoré.\n", stderr)
        return []
    }

    var pages: [OCRPage] = []
    let pageCount = pdf.pageCount
    let limit = min(config.maxPages ?? pageCount, pageCount)

    if let max = config.maxPages, max < pageCount {
        fputs("  (limité aux \(max) premières pages sur \(pageCount))\n", stderr)
    }

    for i in 0..<limit {
        guard let page = pdf.page(at: i) else { continue }

        // Résolution cible : 150 DPI (compromis vitesse / qualité)
        // La taille native en points est multipliée par le facteur d'échelle
        let mediaBox  = page.bounds(for: .mediaBox)
        let scale: CGFloat = 2.0   // 72 pt × 2 = 144 dpi
        let size = CGSize(width: mediaBox.width * scale, height: mediaBox.height * scale)

        guard let bitmap = NSBitmapImageRep(
            bitmapDataPlanes: nil,
            pixelsWide: Int(size.width),
            pixelsHigh: Int(size.height),
            bitsPerSample: 8,
            samplesPerPixel: 4,
            hasAlpha: true,
            isPlanar: false,
            colorSpaceName: .deviceRGB,
            bytesPerRow: 0,
            bitsPerPixel: 0
        ) else { continue }

        let ctx = NSGraphicsContext(bitmapImageRep: bitmap)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = ctx
        ctx?.cgContext.scaleBy(x: scale, y: scale)
        // Fond blanc pour les PDFs avec transparence
        NSColor.white.setFill()
        NSBezierPath.fill(mediaBox)
        page.draw(with: .mediaBox, to: ctx!.cgContext)
        NSGraphicsContext.restoreGraphicsState()

        guard let cg = bitmap.cgImage else { continue }

        let pageNum = i + 1
        if limit > 1 {
            fputs("  → Page \(pageNum)/\(limit)\r", stderr)
            fflush(stderr)
        }

        let lines = runOCR(on: cg, config: config)
        pages.append(OCRPage(source: path, page: pageNum, lines: lines))
    }
    if limit > 1 { fputs("\n", stderr) }
    return pages
}

// ─────────────────────────────────────────────
// MARK: - Traitement par lot
// ─────────────────────────────────────────────

func processAll(config: Config) -> [OCRPage] {
    var all: [OCRPage] = []

    for path in config.paths {
        guard FileManager.default.fileExists(atPath: path) else {
            fputs("Avertissement : '\(path)' introuvable, ignoré.\n", stderr)
            continue
        }
        let ext = (path as NSString).pathExtension.lowercased()
        fputs("Traitement : \(path)\n", stderr)

        if ext == "pdf" {
            all.append(contentsOf: processPDF(path: path, config: config))
        } else {
            all.append(contentsOf: processImage(path: path, config: config))
        }
    }
    return all
}

// ─────────────────────────────────────────────
// MARK: - Formatage de la sortie
// ─────────────────────────────────────────────

func buildPlainText(_ pages: [OCRPage]) -> String {
    var out = ""
    let multiFile = Set(pages.map(\.source)).count > 1
    let multiPage = pages.contains { $0.page > 1 }

    for page in pages {
        if multiFile || multiPage {
            let label = multiPage ? "\(page.source) — page \(page.page)" : page.source
            out += "─── \(label) ───\n"
        }
        out += page.plainText + "\n\n"
    }
    return out.trimmingCharacters(in: .newlines)
}

func buildJSON(_ pages: [OCRPage]) throws -> String {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
    let data = try encoder.encode(pages)
    return String(decoding: data, as: UTF8.self)
}

// ─────────────────────────────────────────────
// MARK: - Point d'entrée
// ─────────────────────────────────────────────

let config = parseArgs(CommandLine.arguments)
let pages  = processAll(config: config)

if pages.isEmpty {
    fputs("Aucun texte extrait.\n", stderr)
    exit(2)
}

let output: String
do {
    output = config.jsonOutput
        ? (try buildJSON(pages))
        : buildPlainText(pages)
} catch {
    fatal("Encodage JSON : \(error.localizedDescription)")
}

if let outPath = config.outputFile {
    do {
        try output.write(toFile: outPath, atomically: true, encoding: .utf8)
        fputs("Résultat écrit dans '\(outPath)'.\n", stderr)
    } catch {
        fatal("Écriture du fichier '\(outPath)' : \(error.localizedDescription)")
    }
    if config.alsoStdout {
        print(output)
    }
} else {
    // Pas de --output : stdout est toujours la destination par défaut
    print(output)
}
