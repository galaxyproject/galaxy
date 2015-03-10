var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Testing the user share form for histories', 0, function suite( test ){
    spaceghost.start();

    // =================================================================== globals and helpers
    var email = spaceghost.user.getRandomEmail(),
        password = '123456';
    if( spaceghost.fixtureData.testUser ){
        email = spaceghost.fixtureData.testUser.email;
        password = spaceghost.fixtureData.testUser.password;
        spaceghost.info( 'Will use fixtureData.testUser: ' + email );
    }
    var email2 = spaceghost.user.getRandomEmail(),
        password2 = '123456';
    if( spaceghost.fixtureData.testUser2 ){
        email2 = spaceghost.fixtureData.testUser2.email;
        password2 = spaceghost.fixtureData.testUser2.password;
    }

    var shareLink = 'a[href^="/history/share?"]',
        shareSubmit = 'input[name="share_button"]',
        firstUserShareButton = '#user-0-popup',
        shareHistoryId = null,
        shareUserId = null;

    function fromUserSharePage( fn ){
        spaceghost.then( function(){
            this.openHomePage( function(){
                this.historyoptions.clickOption( 'Share or Publish' );
            });
            this.waitForNavigation( 'history/sharing', function(){
                this.jumpToMain( function(){
                    this.click( shareLink );
                });
            });
            this.waitForNavigation( 'history/share', function(){
                this.jumpToMain( function(){
                    fn.call( this );
                });
            });
        });
    }

    function thenSwitchUser( email, password ){
        spaceghost.then( function(){
            spaceghost.user.logout();
            spaceghost.user.loginOrRegisterUser( email, password );
        });
        return spaceghost;
    }

    function thenShareWithUser( comment, emailOrId, thenFn ){
        spaceghost.then( function(){
            fromUserSharePage( function(){
                this.test.comment( comment );
                this.fill( 'form#share', {
                    email : emailOrId
                });
                // strangely, casper's submit=true flag doesn't work well here - need to manually push the button
                this.click( shareSubmit );
            });
            spaceghost.then( function(){
                this.jumpToMain( function(){
                    thenFn.call( this );
                });
            });
        });
        return spaceghost;
    }

    // =================================================================== TESTS
    // create user 1 and the test/target history
    spaceghost.user.loginOrRegisterUser( email, password ).openHomePage( function(){
        shareHistoryId = this.api.histories.index()[0].id;
        this.info( 'shareHistoryId: ' + shareHistoryId );
    });
    spaceghost.then( function(){
        // can't share an empty history (for some reason)
        this.api.tools.thenUpload( shareHistoryId, { filepath: '../../test-data/1.bed' });
    });

    // create user 2 and make sure they can't access the history right now
    thenSwitchUser( email2, password2 ).openHomePage( function(){
        shareUserId = this.api.users.index()[0].id;
        this.info( 'shareUserId: ' + shareUserId );

        this.test.comment( 'user2 should not have access to test history' );
        this.api.assertRaises( function(){
            this.api.histories.show( shareHistoryId );
        }, 403, 'History is not accessible by user', 'show failed with error' );
    });

    thenSwitchUser( email, password );
    thenShareWithUser( "should NOT work: share using non-existant user email", 'chunkylover53@aol.com', function(){
        this.test.assertExists( '.errormessage', 'found error message' );
        this.test.assertSelectorHasText( '.errormessage', 'is not a valid Galaxy user', 'wording is good' );
    });
    thenShareWithUser( "should NOT work: share using current user email", email, function(){
        this.test.assertExists( '.errormessage', 'found error message' );
        this.test.assertSelectorHasText( '.errormessage', 'You cannot send histories to yourself', 'wording is good' );
    });
    thenShareWithUser( "should work: share using email", email2, function(){
        this.test.assertExists( firstUserShareButton, 'found user share button' );
        this.test.assertSelectorHasText( firstUserShareButton, email2, 'share button text is email2' );
    });

    // user 2 can now access the history
    thenSwitchUser( email2, password2 ).openHomePage( function(){
        this.test.comment( 'user 2 can now access the history' );
        this.test.assert( !!this.api.histories.show( shareHistoryId ).id );
    });


    // remove share
    thenSwitchUser( email, password ).thenOpen( spaceghost.baseUrl + '/history/sharing', function(){
        this.jumpToMain( function(){
            this.click( firstUserShareButton );
            this.wait( 100, function(){
                this.click( 'a[href^="/history/sharing?unshare_user"]' );
            });
        });
    });
    spaceghost.then( function(){
        this.test.assertDoesntExist( firstUserShareButton, 'no user share button seen' );
    });

    thenSwitchUser( email2, password2 ).openHomePage( function(){
        this.test.comment( 'user2 should not have access to test history (again)' );
        this.api.assertRaises( function(){
            this.api.histories.show( shareHistoryId );
        }, 403, 'History is not accessible by user', 'show failed with error' );
    });


    // should NOT work: share using malformed id
    thenSwitchUser( email, password );
    thenShareWithUser( "should NOT work: share using malformed id", '1234xyz', function(){
        this.test.assertExists( '.errormessage', 'found error message' );
        this.test.assertSelectorHasText( '.errormessage', 'is not a valid Galaxy user', 'wording is good' );
    });
    //spaceghost.then( function(){
    //    // test user share using email
    //    fromUserSharePage( function(){
    //        this.test.comment( 'should NOT work: share using malformed id' );
    //        this.fill( '#share', {
    //            email : '1234xyz'
    //        });
    //        this.click( shareSubmit );
    //    });
    //    spaceghost.then( function(){
    //        this.jumpToMain( function(){
    //            this.test.assertExists( '.errormessage', 'found error message' );
    //            this.test.assertSelectorHasText( '.errormessage', 'is not a valid Galaxy user', 'wording is good' );
    //        });
    //    });
    //});

    // should NOT work: share using current user id
    spaceghost.then( function(){
        var currUserId = spaceghost.api.users.index()[0].id;
        thenShareWithUser( "should NOT work: share using current user id", currUserId, function(){
            this.test.assertExists( '.errormessage', 'found error message' );
            this.test.assertSelectorHasText( '.errormessage',
                'You cannot send histories to yourself', 'wording is good' );
        });
    });
    //// should NOT work: share using current user id
    //spaceghost.then( function(){
    //    var currUserId = spaceghost.api.users.index()[0].id;
    //    // test user share using email
    //    fromUserSharePage( function(){
    //        this.test.comment( 'should NOT work: share using current user id' );
    //        this.debug( 'currUserId: ' + currUserId );
    //        this.fill( 'form#share', {
    //            email : currUserId
    //        });
    //        this.click( shareSubmit );
    //    });
    //    spaceghost.then( function(){
    //        this.jumpToMain( function(){
    //            this.test.assertExists( '.errormessage', 'found error message' );
    //            this.test.assertSelectorHasText( '.errormessage',
    //                'You cannot send histories to yourself', 'wording is good' );
    //        });
    //    });
    //});

    spaceghost.then( function(){
        thenShareWithUser( "should work: share using id", shareUserId, function(){
            this.test.assertExists( firstUserShareButton, 'found user share button' );
            this.test.assertSelectorHasText( firstUserShareButton, email2, 'share button text is email2' );
        });
    });
    //// should work: share using id
    //spaceghost.then( function(){
    //    // test user share using email
    //    fromUserSharePage( function(){
    //        this.test.comment( 'should work: share using id' );
    //        this.fill( '#share', {
    //            email : shareUserId
    //        });
    //        this.click( shareSubmit );
    //    });
    //    spaceghost.then( function(){
    //        this.jumpToMain( function(){
    //            this.test.assertExists( firstUserShareButton, 'found user share button' );
    //            this.test.assertSelectorHasText( firstUserShareButton, email2, 'share button text is email2' );
    //        });
    //    });
    //});

    // user 2 can now access the history
    thenSwitchUser( email2, password2 ).openHomePage( function(){
        this.test.comment( 'user 2 can now access the history' );
        this.test.assert( !!this.api.histories.show( shareHistoryId ).id );
    });

    /*
    */
    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});
