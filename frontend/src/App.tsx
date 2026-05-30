import { BrowserRouter, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import Dashboard from "./pages/Dashboard";
import ReviewQueue from "./pages/ReviewQueue";
import ReviewWorkspace from "./pages/ReviewWorkspace";
import EvaluationCenter from "./pages/EvaluationCenter";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/review-queue" element={<ReviewQueue />} />
        <Route path="/review/:owner/:repo/:number" element={<ReviewWorkspace />} />
        <Route path="/evaluation" element={<EvaluationCenter />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>
  );
}
