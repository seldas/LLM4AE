import { ContextMenu } from "../../lib/interfaces"

interface Props {
    contextMenu: ContextMenu,
    options: string[]
    handleClick: (
        text: string
    ) => void
}

const RelationshipContextMenuDisplay = (props: Props) => {
    return (
        <>
            <ul
                style={{
                    position: 'absolute',
                    top: `${props.contextMenu.y}px`,
                    left: `${props.contextMenu.x}px`,
                    backgroundColor: 'white',
                    border: '1px solid #ccc',
                    padding: '5px',
                    listStyle: 'none',
                    zIndex: 1000,
                }}
            >
                {props.options.map((option) => (
                    <li
                        key={option}
                        style={{
                            cursor: 'pointer',
                            padding: '5px',
                            margin: '5px',
                        }}
                        onClick={() => props.handleClick(option)}
                    >
                        {option}
                    </li>
                ))}
            </ul>
        </>
    )
};

export default RelationshipContextMenuDisplay;