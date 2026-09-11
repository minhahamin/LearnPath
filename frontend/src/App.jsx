import { Link, Route, Routes } from "react-router-dom";

import HistoryPage from "./pages/HistoryPage.jsx";
import InputPage from "./pages/InputPage.jsx";
import ProgressPage from "./pages/ProgressPage.jsx";
import ResultPage from "./pages/ResultPage.jsx";

export default function App() {
  return (
    <>
      <div className="bg-decor" aria-hidden="true">
        <div className="bg-stars" />
        <div className="bg-clouds" />
      </div>
      <div className="app-shell">
        <header className="app-header">
          <Link to="/" className="app-title">
            Learning Curator
          </Link>
          <nav>
            <Link to="/">새 큐레이션</Link>
            <Link to="/history">히스토리</Link>
          </nav>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<InputPage />} />
            <Route path="/roadmaps/:id/progress" element={<ProgressPage />} />
            <Route path="/roadmaps/:id" element={<ResultPage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Routes>
        </main>
      </div>
    </>
  );
}
