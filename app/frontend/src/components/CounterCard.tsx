interface CounterCardProps {
  label: string;
  value: string | number;
  unit?: string;
}

export default function CounterCard({ label, value, unit }: CounterCardProps) {
  return (
    <div className="counter-card">
      <div className="counter-value">
        {value}
        {unit && <span className="counter-unit">{unit}</span>}
      </div>
      <div className="counter-label">{label}</div>
    </div>
  );
}
