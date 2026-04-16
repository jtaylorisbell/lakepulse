/** Human-readable descriptions for each metric, shown in tooltips. */
const descriptions: Record<string, string> = {
  // CPU
  cpu_percent: "CPU usage for a single core",
  cpu_percent_total: "Overall CPU usage across all cores",
  cpu_freq_mhz: "Current CPU clock frequency in MHz",
  load_1m: "Average number of processes waiting for CPU over the last 1 minute",
  load_5m: "Average number of processes waiting for CPU over the last 5 minutes",
  load_15m: "Average number of processes waiting for CPU over the last 15 minutes",

  // Memory
  memory_percent: "Percentage of physical RAM in use",
  memory_used_bytes: "Physical RAM currently in use",
  memory_total_bytes: "Total installed physical RAM",
  swap_percent: "Percentage of swap space in use",
  swap_used_bytes: "Swap space currently in use",

  // Disk
  disk_percent: "Percentage of root partition used",
  disk_used_bytes: "Disk space used on root partition",
  disk_total_bytes: "Total disk space on root partition",
  disk_read_bytes: "Cumulative bytes read from disk since boot",
  disk_write_bytes: "Cumulative bytes written to disk since boot",

  // Network
  net_bytes_sent: "Cumulative bytes sent across all interfaces",
  net_bytes_recv: "Cumulative bytes received across all interfaces",

  // Battery
  battery_percent: "Current battery charge level",
  battery_plugged: "Whether the power adapter is connected",

  // Thermal / Fan / GPU
  thermal_pressure: "System thermal pressure level (0=nominal, 3=critical)",
  fan_speed_rpm: "Fan speed in revolutions per minute",
  gpu_power_watts: "GPU power consumption in watts",
};

export function getDescription(metric: string): string {
  return descriptions[metric] ?? "";
}
