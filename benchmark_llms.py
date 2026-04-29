import asyncio
import time
import os
import json
import csv
from datetime import datetime
from typing import List

from app.config import settings
from app.models import RecommendRequest
from app.services.pipeline import RecommendationPipeline

# Daftar model untuk evaluasi (sesuai request)
MODELS_TO_EVALUATE: List[str] = [
    "ibm-granite/granite-4.0-h-micro",
    "amazon/nova-2-lite-v1",
    "google/gemini-3.1-flash-lite-preview",
    "stepfun/step-3.5-flash:free",
    "google/gemma-2-9b-it",
    "mistralai/mixtral-8x22b-instruct",
    
    
    
]

TEST_INTENT = "lagu pop indonesia buat nemenin coding malam hari"

def generate_html_report(results: list, out_dir: str):
    # Pisahkan model yang sukses dan gagal
    labels = [r["model"] for r in results if r["error"] is None]
    latencies = [r["latency_sec"] for r in results if r["error"] is None]
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Benchmark LLM SmartDiscover</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 2rem auto; color: #333; }}
        h1, h2 {{ text-align: center; }}
        .chart-container {{ width: 100%; height: 400px; margin-bottom: 2rem; position: relative; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
        .error {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Laporan Benchmark LLM</h1>
    <p><strong>Intent:</strong> "{TEST_INTENT}"</p>
    <p><strong>Waktu:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Grafik Latency (Kecepatan)</h2>
    <div class="chart-container">
        <canvas id="latencyChart"></canvas>
    </div>

    <h2>Detail Hasil Evaluasi</h2>
    <table>
        <tr>
            <th>Model</th>
            <th>Waktu (Detik)</th>
            <th>Lagu Ditemukan</th>
            <th>Status</th>
        </tr>
"""
    for r in sorted(results, key=lambda x: (x["error"] is not None, x["latency_sec"])):
        status = f"<span class='error'>Error: {r['error']}</span>" if r["error"] else "Sukses"
        html_content += f"""        <tr>
            <td>{r["model"]}</td>
            <td>{r['latency_sec']:.2f}s</td>
            <td>{r['track_count']}</td>
            <td>{status}</td>
        </tr>
"""
    html_content += f"""    </table>

    <script>
        const ctx = document.getElementById('latencyChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: 'Latency (Detik)',
                    data: {json.dumps(latencies)},
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{ beginAtZero: true, title: {{ display: true, text: 'Detik (Lebih rendah lebih baik)' }} }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as f:
        f.write(html_content)


async def run_benchmark():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("benchmark_results", timestamp)
    os.makedirs(out_dir, exist_ok=True)
    
    print("=" * 60)
    print(f"Mulai Benchmark 6 Model OpenRouter")
    print(f"Topik / Intent: '{TEST_INTENT}'")
    print(f"Output akan disimpan di folder: {out_dir}")
    print("=" * 60)
    print()

    # Inisialisasi satu obyek Request
    request_payload = RecommendRequest(text=TEST_INTENT, target_count=5)

    results = []

    for model_name in MODELS_TO_EVALUATE:
        print(f"🚀 Mengevaluasi Model: {model_name}")
        
        # Override setting / config sebelum init Pipeline
        settings.openrouter_model = model_name
        
        # Buat instansi pipeline baru dengan model yang sudah dioverride
        pipeline = RecommendationPipeline()
        pipeline.llm.model = model_name  # Pastikan di-override juga di client LLM
        
        start_time = time.perf_counter()
        
        try:
            # Eksekusi rekomendasi
            response = await pipeline.run(request_payload)
            elapsed_time = time.perf_counter() - start_time
            
            # Kumpulkan output tracks (untuk analisis akurasi)
            output_tracks = [track.title + " - " + track.artist for track in response.recommendations]
            
            print(f"✅ Selesai: {elapsed_time:.2f} detik")
            print(f"🎵 Lagu ditemukan: {len(output_tracks)}")
            
            # Ambil alasan dari lagu pertama (jika ada) sebagai representasi kualitas teks
            sample_why = response.recommendations[0].why if response.recommendations else "Tidak ada alasan / rekomendasi"

            results.append({
                "model": model_name,
                "latency_sec": elapsed_time,
                "track_count": len(output_tracks),
                "tracks": output_tracks,
                "narrative": sample_why,
                "error": None
            })
            
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            print(f"❌ Error: {elapsed_time:.2f} detik ({str(e)})\n")
            results.append({
                "model": model_name,
                "latency_sec": elapsed_time,
                "track_count": 0,
                "tracks": [],
                "narrative": "",
                "error": str(e)
            })

    print("=" * 60)
    print("🏆 MENYIMPAN HASIL BENCHMARK")
    print("=" * 60)

    # 1. Simpan CSV Summary
    csv_path = os.path.join(out_dir, "summary.csv")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Model", "Latency (s)", "Track Count", "Error"])
        for r in results:
            writer.writerow([r["model"], f"{r['latency_sec']:.2f}", r["track_count"], r["error"] or ""])

    # 2. Simpan JSON Detail (Untuk analisa akurasi)
    json_path = os.path.join(out_dir, "raw_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    # 3. Simpan HTML Report dengan Chart.js
    generate_html_report(results, out_dir)

    print(f"📁 Selesai! Semua file berhasil disimpan di: {out_dir}")
    print(f"   - {csv_path} (Tabel Komparasi)")
    print(f"   - {json_path} (Data Mentah Lagu & Narasi)")
    print(f"   - {os.path.join(out_dir, 'report.html')} (Laporan Visual - Buka via Browser)\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
