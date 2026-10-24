import { useCallback, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** Keep help text readable even when its trigger sits inside clipped panels. */
export default function HelpTip({ text }) {
  const anchorRef = useRef(null);
  const tooltipRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const tooltipId = useId();

  /** Measure both elements and choose a side that remains inside the viewport. */
  const placeTooltip = useCallback(() => {
    const anchor = anchorRef.current;
    const tooltip = tooltipRef.current;
    if (!anchor || !tooltip) return;
    const trigger = anchor.getBoundingClientRect();
    const tip = tooltip.getBoundingClientRect();
    const margin = 12;
    const gap = 9;
    const roomRight = window.innerWidth - trigger.right;
    const roomLeft = trigger.left;
    let left;
    let transform = "translateX(-50%)";
    if (trigger.left < window.innerWidth * 0.34 && roomRight >= tip.width + gap) {
      left = trigger.left;
      transform = "none";
    } else if (trigger.right > window.innerWidth * 0.66 && roomLeft >= tip.width + gap) {
      left = trigger.right - tip.width;
      transform = "none";
    } else {
      left = trigger.left + trigger.width / 2;
    }
    left = Math.max(margin, Math.min(left, window.innerWidth - tip.width - margin));
    const above = trigger.top - tip.height - gap;
    const top = above >= margin ? above : Math.min(trigger.bottom + gap, window.innerHeight - tip.height - margin);
    setPosition({ top, left, transform });
  }, []);

  useLayoutEffect(() => {
    if (!open) return undefined;
    placeTooltip();
    window.addEventListener("resize", placeTooltip);
    window.addEventListener("scroll", placeTooltip, true);
    return () => {
      window.removeEventListener("resize", placeTooltip);
      window.removeEventListener("scroll", placeTooltip, true);
    };
  }, [open, text, placeTooltip]);

  return <>
    <span
      ref={anchorRef}
      className="help-tip"
      tabIndex={0}
      aria-label={`Help: ${text}`}
      aria-describedby={open ? tooltipId : undefined}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    ><span aria-hidden="true">?</span></span>
    {open && createPortal(
      <span ref={tooltipRef} id={tooltipId} className="help-tooltip" role="tooltip" style={position || { visibility: "hidden" }}>{text}</span>,
      document.body,
    )}
  </>;
}
