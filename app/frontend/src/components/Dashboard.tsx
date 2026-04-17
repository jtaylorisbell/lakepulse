import { useEventStream } from "../hooks/useEventStream";
import Header from "./Header";
import ThroughputBar from "./ThroughputBar";
import LiveFeed from "./LiveFeed";
import BotHumanPanel from "./BotHumanPanel";
import EditTypePanel from "./EditTypePanel";
import TopWikisPanel from "./TopWikisPanel";
import BiggestEditsPanel from "./BiggestEditsPanel";
import SearchPanel from "./SearchPanel";
import PipelineHealthPanel from "./PipelineHealthPanel";

export default function Dashboard() {
  const { events, connected } = useEventStream(100);

  return (
    <div className="dashboard">
      <Header connected={connected} />
      <ThroughputBar />

      <div className="main-grid">
        <div className="main-left">
          <LiveFeed events={events} />
        </div>
        <div className="main-right">
          <div className="analytics-row">
            <BotHumanPanel />
            <EditTypePanel />
          </div>
          <div className="analytics-row">
            <TopWikisPanel />
            <BiggestEditsPanel />
          </div>
        </div>
      </div>

      <SearchPanel />
      <PipelineHealthPanel />
    </div>
  );
}
