import { CheckCircle } from 'lucide-react';

/**
 * QuestionCardFooter: the card's status strip (the bank only shows saved questions).
 */
export default function QuestionCardFooter({ isSaved = true }) {
  return (
    <div className="qcard-footer">
      <div className="qcard-footer-actions">
        <div className="qcard-footer-saved-label">
          <CheckCircle size={16} /> {isSaved ? 'Saved in Question Bank' : 'Ready for review'}
        </div>
      </div>
    </div>
  );
}
