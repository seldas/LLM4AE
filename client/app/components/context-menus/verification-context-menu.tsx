import { ContextMenu } from "../../lib/interfaces";

interface Props {
  contextMenu: ContextMenu;
  handleClick: (disputed: boolean) => void;
}

const VerificationContextMenuDisplay = (props: Props) => {
  return (
    <ul
      style={{
        position: 'absolute',
        top: `${props.contextMenu.y}px`,
        left: `${props.contextMenu.x}px`,
        backgroundColor: '#fff',
        border: '1px solid #ccc',
        borderRadius: '8px',
        padding: '6px',
        listStyle: 'none',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        zIndex: 1000,
        animation: 'fadeIn 0.2s ease-in-out',
        minWidth: '140px'
      }}
    >
      <li
        onClick={() => props.handleClick(true)}
        style={{
          cursor: 'pointer',
          padding: '8px 12px',
          marginBottom: '4px',
          borderRadius: '6px',
          backgroundColor: '#fadbd8',
          color: '#a93226',
          fontWeight: 500,
          textAlign: 'center',
          transition: 'background-color 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#f5b7b1';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = '#fadbd8';
        }}
      >
        Dispute
      </li>
      <li
        onClick={() => props.handleClick(false)}
        style={{
          cursor: 'pointer',
          padding: '8px 12px',
          borderRadius: '6px',
          backgroundColor: '#d6eaf8',
          color: '#21618c',
          fontWeight: 500,
          textAlign: 'center',
          transition: 'background-color 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#aed6f1';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = '#d6eaf8';
        }}
      >
        Undispute
      </li>
    </ul>
  );
};

export default VerificationContextMenuDisplay;
