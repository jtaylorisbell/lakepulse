interface HeaderProps {
  connected: boolean;
}

export default function Header({ connected }: HeaderProps) {
  return (
    <header>
      <div className="header-row">
        <div>
          <h1>LakePulse</h1>
          <p className="subtitle">Live Wikipedia Edits — Real-time streaming through Databricks</p>
        </div>
        <div className={`live-indicator ${connected ? "" : "disconnected"}`}>
          <span className="live-dot" />
          {connected ? "LIVE" : "RECONNECTING"}
        </div>
      </div>
    </header>
  );
}
