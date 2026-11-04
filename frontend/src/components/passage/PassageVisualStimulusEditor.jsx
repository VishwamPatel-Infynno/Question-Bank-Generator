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
      className="btn-ghost passage-stimulus-discard-btn"
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
        <span className="badge badge-emerald passage-stimulus-editor-badge">
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

