import { Trash2 } from 'lucide-react';
import VisualStimulusViewer from '../question/VisualStimulusViewer';

/**
 * PassageVisualStimulusEditor
 *
 * Dedicated unified figure showcase card for an MCAT reading passage.
 * Displays the visual stimulus clearly and provides a direct 'Discard Image'
 * option if an image is attached. If no image exists, renders nothing to eliminate clutter.
 */
export default function PassageVisualStimulusEditor({
  imageUrl = '',
  imageSvg = '',
  imageDescription = '',
  onDescriptionChange = null,
  onDiscardImage = null
}) {
  const hasConfiguredVisual = Boolean(imageUrl || imageSvg);

  if (!hasConfiguredVisual) {
    return null;
  }

  const discardAction = onDiscardImage ? (
    <button
      type="button"
      onClick={onDiscardImage}
      className="btn-ghost"
      style={{
        padding: '3px 8px',
        fontSize: '0.675rem',
        color: 'var(--status-danger)',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px'
      }}
      title="Remove this image from the passage"
    >
      <Trash2 size={11} />
      <span>Discard Image</span>
    </button>
  ) : null;

  return (
    <VisualStimulusViewer
      imageUrl={imageUrl}
      imageSvg={imageSvg}
      imageDescription={imageDescription}
      headerTitle="Passage Figure / Diagram"
      badgeExtra={
        <span
          className="badge badge-emerald"
          style={{ fontSize: '0.625rem', padding: '2px 6px', fontWeight: 600 }}
        >
          Attached
        </span>
      }
      actionsExtra={discardAction}
      isEditing={Boolean(onDescriptionChange)}
      editedDescription={imageDescription}
      onDescriptionChange={onDescriptionChange}
    />
  );
}

