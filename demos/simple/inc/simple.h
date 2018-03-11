#include <gtkmm.h>

namespace simple
{
    class simple_ui : public Gtk::ApplicationWindow
    {
    public:
        simple_ui(BaseObjectType * cObj, 
            Glib::RefPtr<Gtk::Builder> const & builder);
        void on_click();
    };
}

