import { Link, useLocation } from "react-router-dom";
import { useApp } from "../../context/AppContext";

const navLinks = [
  { to: "/chat", label: "Chat" },
  { to: "/documents", label: "Documents" },
  { to: "/knowledge", label: "Knowledge Base" },
  { to: "/analytics", label: "Analytics" },
  { to: "/agents", label: "Agents" },
  { to: "/settings", label: "Settings" },
];

function StatusPill({ ok, label }) {
  return (
    <div className="hidden lg:flex items-center gap-2 text-xs text-gray-400">
      <span className={`status-dot ${ok ? "ok" : "bad"}`} />
      <span>{label}</span>
    </div>
  );
}

export default function Navbar() {
  const { pathname } = useLocation();
  const { health } = useApp();
  const hideNav = pathname === "/";

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-surface/90 backdrop-blur-md">
      <div className="max-w-[1600px] mx-auto px-4 h-14 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-lg">
            🦊
          </div>
          <span className="font-semibold text-white hidden sm:block">FoxZilla</span>
        </Link>

        {!hideNav && (
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  pathname === to
                    ? "bg-accent/10 text-accent font-medium"
                    : "text-gray-400 hover:text-gray-200 hover:bg-surface-elevated"
                }`}
              >
                {label}
              </Link>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-4 shrink-0">
          <StatusPill ok={health?.llm?.ok} label="Llamafile Connected" />
          <StatusPill ok={health?.encoderfile?.ok} label="Encoderfile Ready" />
          <StatusPill ok={health?.mcpd?.ok} label="MCPD Connected" />
          {hideNav && (
            <Link to="/chat" className="btn-primary text-xs py-2 px-4">
              Open App
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
