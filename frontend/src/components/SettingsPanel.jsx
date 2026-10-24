/** Persist campaign tone and rule preferences whenever the player changes them. */
export default function SettingsPanel({ settings, onChange, disabled }) {
  return (
    <section className="side-card settings-card">
      <div className="side-title"><span className="eyebrow">CAMPAIGN SETTINGS</span><span className="ornament">⚙</span></div>
      <label>Difficulty<select disabled={disabled} value={settings.difficulty} onChange={(event) => onChange({ ...settings, difficulty: event.target.value })}>{["Easy", "Moderate", "Hard"].map((option) => <option key={option}>{option}</option>)}</select></label>
      <label>Play mode<select disabled={disabled} value={settings.mode} onChange={(event) => onChange({ ...settings, mode: event.target.value })}>{["Dice", "Narrative", "Hybrid"].map((option) => <option key={option}>{option}</option>)}</select></label>
      <label>Tone<input disabled={disabled} maxLength="80" value={settings.tone} onChange={(event) => onChange({ ...settings, tone: event.target.value })} /></label>
      <p className="settings-caption">Changes apply to the next narrator turn.</p>
    </section>
  );
}
