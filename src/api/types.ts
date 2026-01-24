export type Section = { id: string; display: string };
export type GamePreview = {
	name: string;
	game_id: string;
	page_url?: string;
	present?: boolean;
	section?: string;
};
