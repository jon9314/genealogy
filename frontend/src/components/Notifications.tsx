import { useEffect, useState } from "react";
import { getNotifications, clearNotification } from "../lib/api";

interface Notification {
  id: string;
  message: string;
  type: "success" | "error";
}

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await getNotifications();
      setNotifications(data);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleClear = async (id: string) => {
    await clearNotification(id);
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  return (
    <div style={{ position: "fixed", top: "1rem", right: "1rem", zIndex: 1000 }}>
      {notifications.map((n) => (
        <div
          key={n.id}
          className="card"
          style={{
            background: n.type === "success" ? "#22c55e" : "#ef4444",
            color: "white",
            padding: "1rem",
            marginBottom: "1rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <p>{n.message}</p>
          <button onClick={() => handleClear(n.id)} style={{ background: "none", border: "none", color: "white", fontSize: "1.5rem", cursor: "pointer" }}>
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
