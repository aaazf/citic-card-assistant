import { useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { AdminShell } from "@/components/admin-shell";
import { CustomerShell } from "@/components/customer-shell";
import { KnowledgeWelcome } from "@/components/knowledge-welcome";
import { ChatPage } from "@/pages/chat-page";
import { ConversationsPage } from "@/pages/conversations-page";
import { EvalPage } from "@/pages/eval-page";
import { KnowledgePage } from "@/pages/knowledge-page";
import { SettingsPage } from "@/pages/settings-page";

const LANDING_SEEN_KEY = "personal-knowledge:landing-seen";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [landingSeen, setLandingSeen] = useState(
    () => window.localStorage.getItem(LANDING_SEEN_KEY) === "1",
  );

  function enterSystem() {
    window.localStorage.setItem(LANDING_SEEN_KEY, "1");
    setLandingSeen(true);
    navigate("/", { replace: true });
  }

  const isAdminPath = location.pathname.startsWith("/admin");

  if (!landingSeen && !isAdminPath && location.pathname !== "/welcome") {
    return <KnowledgeWelcome onEnter={enterSystem} />;
  }

  return (
    <Routes>
      <Route
        path="welcome"
        element={<KnowledgeWelcome onEnter={enterSystem} />}
      />
      <Route element={<CustomerShell />}>
        <Route index element={<ChatPage />} />
      </Route>
      <Route path="admin" element={<AdminShell />}>
        <Route index element={<Navigate to="knowledge" replace />} />
        <Route path="knowledge" element={<KnowledgePage />} />
        <Route path="conversations" element={<ConversationsPage />} />
        <Route path="chat" element={<ChatPage variant="staff" />} />
        <Route path="eval" element={<EvalPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
