"use client";

import { useState } from "react";
import { UploadSection } from "@/components/upload-section";
import { Dashboard } from "@/components/dashboard";
import { Navbar } from "@/components/navbar";
import { saveRun, saveIntervals } from "@/lib/supabase";

export default function Home() {
  const [result, setResult] = useState<any>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  async function handleResult(r: any, file: File) {
    setResult(r);
    setUploadedFile(file);
    // Persist to Supabase in background (non-blocking)
    try {
      await saveRun(r);
      if (r.schedule?.length) {
        await saveIntervals(r.run_id, r.schedule);
      }
    } catch {
      // Supabase not configured yet — silently skip
    }
  }

  return (
    <div className="min-h-screen bg-[#080d1a]">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 py-8">
        {!result ? (
          <UploadSection onResult={handleResult} />
        ) : (
          <Dashboard
            result={result}
            uploadedFile={uploadedFile!}
            onReset={() => setResult(null)}
          />
        )}
      </main>
    </div>
  );
}
