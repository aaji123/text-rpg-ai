/** Let the player resume a saved campaign or begin a new one. */
export default function StorySelector({ stories, selectedId, onSelect, onCreate }) {
  return (
    <div className="story-selector">
      <select value={selectedId || ""} onChange={(event) => onSelect(event.target.value)} aria-label="Select story">
        <option value="" disabled>Select a story</option>
        {stories.map((story) => <option key={story.id} value={story.id}>{story.name}</option>)}
      </select>
      <button className="new-story" onClick={onCreate}>＋ New story</button>
    </div>
  );
}
