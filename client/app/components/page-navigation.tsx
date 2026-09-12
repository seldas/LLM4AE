import { Dispatch } from "react";
import { DocActions, DocActionTypes } from "../lib/doc-reducer";

interface Props {
    currentPageIndex: number,
    pageCount: number,
    dispatch: Dispatch<DocActions>,
}

const PageNavigation = (props: Props) => (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: '10px', gap: '5px' }}>
        {/* Previous Page Button */}
        <button onClick={() => props.dispatch({type: DocActionTypes.PREV_PAGE})} disabled={props.currentPageIndex === 0}>
            &lt;
        </button>

        {/* Page Numbers */}
        {props.pageCount <= 5 ? (
            // Display all page numbers if there are 5 or fewer pages
            Array.from( { length: props.pageCount }, (_, i) => i + 1).map(index => (
                <button
                    key={index}
                    onClick={() => props.dispatch({type: DocActionTypes.CHANGE_PAGE, payload: { index }})}
                    style={{
                        backgroundColor: index === props.currentPageIndex ? '#ddd' : 'transparent',
                        border: 'none',
                        padding: '5px',
                        cursor: 'pointer'
                    }}
                >
                    {index}
                </button>
            ))
        ) : (
            // Display condensed page numbers with ellipsis if there are more than 5 pages
            <>
                <button
                    onClick={() => props.dispatch({type: DocActionTypes.CHANGE_PAGE, payload: { index: 0 }})}
                    style={{
                        backgroundColor: props.currentPageIndex === 0 ? '#ddd' : 'transparent',
                        border: 'none',
                        padding: '5px',
                        cursor: 'pointer'
                    }}
                >
                    1
                </button>
                {props.currentPageIndex > 2 && <span>...</span>}
                {props.currentPageIndex > 1 && props.currentPageIndex !== 0 && (
                    <button
                        onClick={() => props.dispatch({type: DocActionTypes.CHANGE_PAGE, payload: { index: props.currentPageIndex - 1 }})}
                        style={{
                            backgroundColor: 'transparent',
                            border: 'none',
                            padding: '5px',
                            cursor: 'pointer'
                        }}
                    >
                        {props.currentPageIndex}
                    </button>
                )}
                {props.currentPageIndex !== 0 && props.currentPageIndex !== props.pageCount - 1 && (
                    <button
                        onClick={() => props.dispatch({type: DocActionTypes.CHANGE_PAGE, payload: { index: props.currentPageIndex  }})}
                        style={{
                            backgroundColor: '#ddd',
                            border: 'none',
                            padding: '5px',
                            cursor: 'pointer'
                        }}
                    >
                        {props.currentPageIndex + 1}
                    </button>
                )}
                {props.currentPageIndex < props.pageCount - 2 && (
                    <button
                        onClick={() => props.dispatch({type: DocActionTypes.CHANGE_PAGE, payload: { index: props.currentPageIndex + 1}})}
                        style={{
                            backgroundColor: 'transparent',
                            border: 'none',
                            padding: '5px',
                            cursor: 'pointer'
                        }}
                    >
                        {props.currentPageIndex + 2}
                    </button>
                )}
                {props.currentPageIndex < props.pageCount - 3 && <span>...</span>}
                <button
                    onClick={() => props.dispatch({type: DocActionTypes.CHANGE_PAGE, payload: { index: props.pageCount - 1}})}
                    style={{
                        backgroundColor: props.currentPageIndex === props.pageCount ? '#ddd' : 'transparent',
                        border: 'none',
                        padding: '5px',
                        cursor: 'pointer'
                    }}
                >
                    {props.pageCount}
                </button>
            </>
        )}

        {/* Next Page Button */}
        <button onClick={() => props.dispatch({type: DocActionTypes.NEXT_PAGE})} disabled={props.currentPageIndex === props.pageCount - 1}>
            &gt;
        </button>
    </div>
);

export default PageNavigation;
