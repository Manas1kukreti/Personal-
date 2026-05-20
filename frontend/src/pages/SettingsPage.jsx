import React from "react";
import { useEffect, useState } from "react";
import { FiCheckCircle, FiLock, FiSave, FiShield, FiUser } from "react-icons/fi";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

export default function SettingsPage() {
  const { user, updateUser } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [profileBusy, setProfileBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [profileMessage, setProfileMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [profileError, setProfileError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwords, setPasswords] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });

  useEffect(() => {
    setName(user?.name || "");
  }, [user?.name]);

  async function saveProfile(event) {
    event.preventDefault();
    setProfileMessage("");
    setProfileError("");

    if (name.trim().length < 2) {
      setProfileError("Name must be at least 2 characters.");
      return;
    }

    setProfileBusy(true);
    try {
      const response = await api.patch("/auth/me", { name: name.trim() });
      updateUser(response.data);
      setProfileMessage("Account name updated.");
    } catch (err) {
      setProfileError(err.response?.data?.detail || "Could not update account name.");
    } finally {
      setProfileBusy(false);
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    setPasswordMessage("");
    setPasswordError("");

    if (passwords.newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (passwords.newPassword !== passwords.confirmPassword) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setPasswordBusy(true);
    try {
      await api.post("/auth/change-password", {
        current_password: passwords.currentPassword,
        new_password: passwords.newPassword
      });
      setPasswords({ currentPassword: "", newPassword: "", confirmPassword: "" });
      setPasswordMessage("Password changed successfully.");
    } catch (err) {
      setPasswordError(err.response?.data?.detail || "Could not change password.");
    } finally {
      setPasswordBusy(false);
    }
  }

  function updatePasswordField(name, value) {
    setPasswords((current) => ({ ...current, [name]: value }));
  }

  return (
    <div className="app-page settings-page">
      <section className="settings-header">
        <div>
          <h1>Settings</h1>
          <p>Manage your profile identity and account security.</p>
        </div>
        <div className="settings-security-chip">
          <FiShield />
          Protected account controls
        </div>
      </section>

      <section className="settings-grid">
        <form className="elevated-panel fintech-card settings-card" onSubmit={saveProfile}>
          <div className="settings-card-title">
            <div className="settings-icon">
              <FiUser />
            </div>
            <div>
              <h2>Account Profile</h2>
              <p>Update the name shown across LedgerFlow.</p>
            </div>
          </div>

          <div className="settings-readonly-row">
            <span>Email</span>
            <strong>{user?.email || "-"}</strong>
          </div>
          <div className="settings-readonly-row">
            <span>Role</span>
            <strong>{user?.role || "-"}</strong>
          </div>

          <label className="settings-field">
            <span>Account name</span>
            <input
              className="form-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              minLength={2}
              maxLength={120}
              required
              placeholder="Your full name"
            />
          </label>

          {profileError && <Message tone="error" text={profileError} />}
          {profileMessage && <Message tone="success" text={profileMessage} />}

          <button className="primary-button settings-action" disabled={profileBusy || name.trim() === user?.name}>
            <FiSave /> {profileBusy ? "Saving..." : "Save profile"}
          </button>
        </form>

        <form className="elevated-panel fintech-card settings-card" onSubmit={changePassword}>
          <div className="settings-card-title">
            <div className="settings-icon">
              <FiLock />
            </div>
            <div>
              <h2>Password</h2>
              <p>Use your current password to confirm this change.</p>
            </div>
          </div>

          <label className="settings-field">
            <span>Current password</span>
            <input
              className="form-input"
              type="password"
              value={passwords.currentPassword}
              onChange={(event) => updatePasswordField("currentPassword", event.target.value)}
              required
              autoComplete="current-password"
            />
          </label>

          <label className="settings-field">
            <span>New password</span>
            <input
              className="form-input"
              type="password"
              value={passwords.newPassword}
              onChange={(event) => updatePasswordField("newPassword", event.target.value)}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </label>

          <label className="settings-field">
            <span>Confirm new password</span>
            <input
              className="form-input"
              type="password"
              value={passwords.confirmPassword}
              onChange={(event) => updatePasswordField("confirmPassword", event.target.value)}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </label>

          {passwordError && <Message tone="error" text={passwordError} />}
          {passwordMessage && <Message tone="success" text={passwordMessage} />}

          <button className="primary-button settings-action" disabled={passwordBusy}>
            <FiLock /> {passwordBusy ? "Changing..." : "Change password"}
          </button>
        </form>
      </section>
    </div>
  );
}

function Message({ tone, text }) {
  return (
    <div className={`settings-message settings-message-${tone}`}>
      {tone === "success" && <FiCheckCircle />}
      <span>{text}</span>
    </div>
  );
}
