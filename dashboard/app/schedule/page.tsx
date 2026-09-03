"use client";

import { useEffect, useState } from "react";
import {
  listSchedules, createSchedule, updateSchedule, deleteSchedule, formatDate,
} from "@/lib/api";
import type { Schedule } from "@/lib/api";

// ============================================================
// SCHEDULE PAGE — Manage automated video generation schedules
// ============================================================

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function SchedulePage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);

  // --- New schedule form state ---
  const [name, setName] = useState("Daily Documentary");
  const [frequency, setFrequency] = useState("daily");
  const [selectedDays, setSelectedDays] = useState([1, 3, 5]);
  const [timeOfDay, setTimeOfDay] = useState("09:00");
  const [format, setFormat] = useState("long");
  const [autoUpload, setAutoUpload] = useState(false);

  useEffect(() => {
    loadSchedules();
  }, []);

  async function loadSchedules() {
    try {
      const data = await listSchedules();
      setSchedules(data);
    } catch {
      // --- API offline ---
    }
    setLoading(false);
  }

  async function handleCreate() {
    try {
      await createSchedule({
        name,
        frequency,
        days_of_week: selectedDays.join(","),
        time_of_day: timeOfDay,
        format,
        auto_upload: autoUpload,
      });
      setShowForm(false);
      loadSchedules();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to create schedule");
    }
  }

  async function handleToggle(id: string, enabled: boolean) {
    try {
      await updateSchedule(id, { enabled: !enabled });
      loadSchedules();
    } catch {
      // --- Handle error ---
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this schedule?")) return;
    try {
      await deleteSchedule(id);
      setSchedules(schedules.filter((s) => s.id !== id));
    } catch {
      // --- Handle error ---
    }
  }

  function toggleDay(day: number) {
    if (selectedDays.includes(day)) {
      setSelectedDays(selectedDays.filter((d) => d !== day));
    } else {
      setSelectedDays([...selectedDays, day].sort());
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      {/* --- Page header --- */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold mb-1">Schedule</h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            Automate video generation on a recurring basis
          </p>
        </div>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            New Schedule
          </button>
        )}
      </div>

      {/* --- Create schedule form --- */}
      {showForm && (
        <div className="card mb-6">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--color-text-secondary)" }}>
            NEW SCHEDULE
          </h3>

          {/* --- Name --- */}
          <div className="mb-4">
            <label className="block text-xs font-semibold mb-1.5" style={{ color: "var(--color-text-muted)" }}>
              Schedule Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full"
            />
          </div>

          {/* --- Days of week --- */}
          <div className="mb-4">
            <label className="block text-xs font-semibold mb-2" style={{ color: "var(--color-text-muted)" }}>
              Days
            </label>
            <div className="flex gap-2">
              {DAY_NAMES.map((day, i) => (
                <button
                  key={day}
                  onClick={() => toggleDay(i)}
                  className="w-10 h-10 rounded-lg text-xs font-semibold transition-colors"
                  style={{
                    background: selectedDays.includes(i)
                      ? "rgba(196, 149, 106, 0.15)"
                      : "var(--color-surface-2)",
                    border: `1px solid ${selectedDays.includes(i) ? "var(--color-accent)" : "var(--color-border)"}`,
                    color: selectedDays.includes(i) ? "var(--color-accent)" : "var(--color-text-muted)",
                  }}
                >
                  {day}
                </button>
              ))}
            </div>
          </div>

          {/* --- Time and format row --- */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold mb-1.5" style={{ color: "var(--color-text-muted)" }}>
                Time
              </label>
              <input
                type="time"
                value={timeOfDay}
                onChange={(e) => setTimeOfDay(e.target.value)}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5" style={{ color: "var(--color-text-muted)" }}>
                Format
              </label>
              <select value={format} onChange={(e) => setFormat(e.target.value)} className="w-full">
                <option value="long">Long (10-15 min)</option>
                <option value="mid">Mid (6-10 min)</option>
                <option value="short">Short (60s)</option>
              </select>
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoUpload}
                  onChange={(e) => setAutoUpload(e.target.checked)}
                  className="w-4 h-4 rounded accent-[var(--color-accent)]"
                />
                <span className="text-sm">Auto-upload</span>
              </label>
            </div>
          </div>

          {/* --- Form actions --- */}
          <div className="flex gap-3 mt-6">
            <button onClick={handleCreate} className="btn btn-primary">
              Create Schedule
            </button>
            <button onClick={() => setShowForm(false)} className="btn btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* --- Existing schedules --- */}
      {schedules.length === 0 && !showForm ? (
        <div className="card text-center py-12">
          <p className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>
            No schedules configured
          </p>
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            Create a schedule to auto-generate videos on a recurring basis
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {schedules.map((sched) => (
            <div key={sched.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-base font-bold">{sched.name}</h3>
                    <span
                      className={`badge ${sched.enabled ? "badge-success" : "badge-neutral"}`}
                    >
                      {sched.enabled ? "Active" : "Paused"}
                    </span>
                  </div>

                  {/* --- Schedule details --- */}
                  <div className="flex items-center gap-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
                    <span>
                      {sched.days_of_week
                        .split(",")
                        .map((d) => DAY_NAMES[parseInt(d)])
                        .join(", ")}
                    </span>
                    <span>at {sched.time_of_day}</span>
                    <span>{sched.format.toUpperCase()}</span>
                    {sched.auto_upload ? (
                      <span style={{ color: "var(--color-accent)" }}>Auto-upload ON</span>
                    ) : null}
                  </div>

                  {sched.last_run && (
                    <p className="text-xs mt-2" style={{ color: "var(--color-text-muted)" }}>
                      Last run: {formatDate(sched.last_run)}
                    </p>
                  )}
                </div>

                {/* --- Actions --- */}
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleToggle(sched.id, !!sched.enabled)}
                    className="btn btn-secondary text-xs"
                  >
                    {sched.enabled ? "Pause" : "Enable"}
                  </button>
                  <button
                    onClick={() => handleDelete(sched.id)}
                    className="btn btn-danger text-xs"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
