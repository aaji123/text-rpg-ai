/** Offer a concise, keyboard-accessible explanation beside a form control. */
export default function HelpTip({ text }) {
  return <span className="help-tip" tabIndex={0} title={text} aria-label={`Help: ${text}`}><span aria-hidden="true">?</span><span className="help-tooltip" role="tooltip">{text}</span></span>;
}
